# M0 Spike 验证报告

> 日期: 2026-08-08 · 工具链: clang 22.1.8 (--target=x86_64-w64-mingw32) + gcc 16.1.0 (MinGW-w64) · mcpp 2026.8.8.2
> 探针位置: OS 临时目录 (%TMP%/opencode/boost-m0/), 未入仓库
> include 路径: 因 M1 未完成, 用 deps/boost/libs/*/include 联合路径 (161 个) 代替顶层 boost/ 汇总根

## 结论: 全部 4 探针双编译器通过, 模式成立

| 探针 | 验证内容 | clang 22 | gcc 16 |
|---|---|---|---|
| 1 optional | export using 类模板跨模块实例化 + 自由运算符 | PASS | PASS |
| 2 mp11 | 纯模板库 + 嵌套命名空间拼写 + 模板模板实参 | PASS | PASS |
| 3 container | friend-in-class 运算符 ADL | PASS | PASS (需修正见下) |
| 4 filesystem | 模块声明 ↔ 静态库定义链接 (10 个 src.cpp) | PASS | PASS |

## 关键发现 (生成器/封装规则依据)

### 1. export 写法 (opencv 风格在两编译器均成立)
```
export namespace boost { using boost::optional; using boost::operator==; }        // 顶层命名空间
export namespace boost { namespace mp11 { using boost::mp11::mp_list; } }         // 嵌套命名空间拼写保持
```
- 类/模板/变量/枚举: 直接 `using` 即可
- **自由函数运算符必须显式 `using boost::operator==;`** (一次导入全部重载); optional/filesystem::path 都是此类
- **friend-in-class 运算符 (container::vector) 无需导出** — 类可达后 ADL 自动找到, 且 friend 无法 using 导出
- 消费者用 `boost::optional<int> a(3)` 等原生拼写; 实例化、static_assert、模板模板实参 (mp_plus) 全部跨模块正常

### 2. gcc 特有的两个坑 (clang 无)
- **坑 A: GMF 全局实体在模板实例化点不可见**。boost::container 的 placement_new.hpp 在全局作用域定义
  `operator new(size_t, void*, boost_container_new_t)`, 消费者实例化 `dtl::construct_type` 时 gcc 找不到。
  修复: 模块 purview 加 `export using ::operator new; export using ::operator delete;`
  (显式重定义不行 — gcc 报 redefinition; using-declaration 可)
- **坑 B: 消费者文本 include 与模块 GMF 相同的头 → 冲突**
  (`#include <type_traits>` + import → "conflicting declaration of std::integral_constant" / "__is_constant_evaluated redefinition")。
  clang 容忍, gcc 禁止。
  修复 (消费者侧, 两选一):
  - **首选: `import std;`** — 需先一次性 `g++ -std=c++23 -fmodules --compile-std-module` 生成
    `gcm.cache/std.gcm` (gcc 15+ 支持; gcc 16 mingw 实测可用, 见下方补充验证)。
    全工程编译统一用 `-fmodules` (非 `-fmodules-ts`)。opencv-m 的 gcc CI 走的正是此路径。
  - 备选: header unit `import <string>;` (gcc 14+ 支持, 实测通过; 无需 std 模块文件)。
  - `--compile-std-module` 在 mingw 上会顺带尝试链接一个自检 exe 报 WinMain 未定义 —
    仅噪音, `std.gcm`/`std.compat.gcm` 照常产出, 可忽略 (2>/dev/null 或接受该退出码)。

> 补充验证 (用户指正后): gcc 16 + mingw 下 `import std;` 完全可用。
> probe1 (optional) 与 probe4 (filesystem 编译库) 均以 `import std;` + `import boost.X;` 组合通过 (exit 0),
> 含 std::string 与 const char* 比较、std::vector 使用。gcc 消费者模式升级为与 opencv-m 一致:
> `import std;` + `import boost.*;`, header unit 仅作无 std 模块环境的后备。

### 3. 消费者 std 表面是必选项
boost 实体签名引用 std 类型 (`path::string()` 返回 std::string), 其运算符在模块外不可见:
`p.parent_path().string() != "a/b"` 在纯 import 消费者 TU 中编译失败 → 消费者必须自带 std 表面
(clang: include 或 import std; gcc: **import std;** (需 `--compile-std-module` 预编译) 或 header unit)。
这是设计使然, 文档需写明; 推荐消费者统一 `import std;`。

### 4. 编译库链接无问题
- 模块 TU (头文件声明) + `libs/*/src/*.cpp` 编译的静态库 (定义) 直接链接, mangling 一致
- filesystem 的 exists/create_directories/current_path/remove_all 均为 .cpp 内符号, 链接解析正常
- 注意: clang 链接需 `-lpthread` (winpthreads); mingw 运行时 DLL 需在 PATH (标准 mingw 行为)

### 5. 旁路头混合 (macros.hpp 方案) 在 gcc 可用
消费者 `#include <boost/version.hpp>` + `import boost.optional;` 通过 (exit 0) —
前提: 旁路头内容与模块 GMF include 集不相交 (version.hpp 未被 optional 模块包含)。macros.hpp 设计须遵守此约束。

### 6. 规模
optional 模块 BMI 7.6MB; filesystem 更大。每库一模块的粒度下消费者只为其 import 的模块付编译代价, 可接受。

## 风险遗留
- MSVC 行为未验证 (本机无 MSVC; 采用 clang/gcc 双编译器 CI, 与 opencv-m 一致)
- gcc 的 GMF 实例化缺口为编译器实现限制, 可能随版本变动; 封装层用 curated 清单 + smoke 测试兜底
- 顶层 boost/ 汇总根仍缺失 (M1 修复), 探针用的联合 include 路径与官方根布局可能有个别差异, M1 后需回归

## 对 M2 生成器的输入
1. 导出规则: 命名空间实体 → using; 自由运算符 → using operatorX; friend 运算符 → 跳过
2. gcc 补丁清单 (curated): GMF 全局辅助实体需 `export using ::operator new;` 式再导出 (已知: container 的 placement_new)
3. 依赖闭包: 签名中引用的 boost 实体须连带导出 (filesystem → system::error_code, 下阶段验证)
4. 每库 gcc smoke 测试必须成为标准 CI 项 (gcc 是最严格的消费者环境)
