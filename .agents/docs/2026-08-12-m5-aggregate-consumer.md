# M5 过程记录: 汇总模块 `import boost;` + 示例项目 + gcc/mingw 多重定义排查与 B' 修复

> 日期: 2026-08-12 · 状态: **M5 完成 (B' 已实施)** — llvm/msvc 28/28 绿, 示例全过;
> gcc/mingw 25/28 (regex/system/filesystem 阻塞已解; url/thread/variant 为基线既有
> 失败, **移交 M6 CI 适配**, 见 §5)
> 计划: boost-mcpp-module-plan.md M5 · 前置: M0–M4 (27 库模块层 + 8 编译库接入)

## 1. 目标

- `src/boost.cppm` 汇总模块: 消费者 `import boost;` 一键到达全部子模块。
- 示例项目: 依赖本包, 跑 filesystem 读写 + json 序列化 + regex 匹配。
- 用户指定: 不用 `mcpp new`, 直接在 `./examples/` 建 `mcpp.toml` + 源文件,
  `[dependencies] boost.boost = { path = ".." }` 引依赖。

## 2. 实施内容

### 2.1 汇总模块 `src/boost.cppm`

`export module boost;` + `export import` 全部 27 个子模块
(algorithm/any/chrono/container_hash/core/endian/filesystem/io/iterator/json/mp11/
optional/program_options/range/rational/regex/scope/scope_exit/stacktrace/
static_string/system/thread/tuple/type_traits/url/variant/variant2)。
`mcpp.toml` sources 首位追加 `"src/boost.cppm"`。

### 2.2 示例项目 `examples/`

```
examples/
├── mcpp.toml        # [package] boost-example + [dependencies] boost.boost = { path = ".." }
└── src/main.cpp      # import boost; — filesystem 读写 + json 序列化 + regex 匹配
```

- `mcpp.toml`: 无 `[build]` 段 — 消费者只 import, 不用自带 include 根。
- `main.cpp` 三节演示, 各节独立 CHECK 断言; 未 include 任何 `<boost/...>` 头。
- **排障记录** (示例本身):
  - `boost::BOOST_VERSION` 是 core 模块 re-homed 的 constexpr; 示例最初写
    `BOOST_VERSION_STRING` 拼写 (宏面拼写) → 模块面不存在 → 改用 `boost::BOOST_VERSION`。
  - Windows 文本模式 `\n`→`\r\n`: 首次断言 `file_size == 19` 实际 20; 去掉行尾换行后按
    纯文本写入, 断言 `file_size == 19`。

### 2.3 llvm/msvc (默认风味) 验证

- `mcpp test` → **28/28 绿** (含新增 `src/boost.cppm` 与 `src/boost_system_extras.cpp` 后全量回归)。
- `examples/` → `mcpp build` + `mcpp run` 三节全过, 输出
  `import boost; example — build 109100` / `all examples passed`。

## 3. 阻塞问题: gcc/mingw 链接失败 (multiple definition)

### 3.1 现象

gcc/mingw 风味 `mcpp test regex` 链接失败; 与 M5 改动无关 —
`git stash` 后回 M4 基线同样复现。

冲突符号 (全部是 inline 函数内的局部 static):

| 符号 | 出处 |
|---|---|
| `get_default_error_string(...)::s_default_error_messages` | regex_traits_defaults.hpp |
| `lookup_default_collate_name(...)::def_coll_names` / `def_multi_coll` | regex_traits_defaults.hpp |
| `mem_block_cache::instance()::block_cache` (+ guard var) | mem_block_cache.hpp |
| `get_default_class_id<char>(...)::data` / `ranges` | regex_traits_defaults.hpp |

报错双方: 消费者 TU (`tests/regex.o` / 示例 `main.o`, import boost.regex) ↔
regex 库 TU (`libs/regex/src/{posix_api,wide_posix_api}.o`)。

**修订** (本轮 full suite 跑通后): §3.1 原文 "filesystem/json/其余 26 测试在 gcc 下
全绿, 仅 regex 挂" **不实** — 全量跑 gcc 暴露 system/filesystem/url/thread/variant
共 5 项同样失败 (system/filesystem 同为本 § 的 static 模式, 已由 B' 修复; 其余见 §5)。
M4 文档 "gcc/mingw 28/28 绿" 亦不可信 (见 §3.4 与 §5)。

### 3.2 根因分析

- `regex.inc` 有 186 个 `using boost::re_detail_600::...` 重导出。
- 但冲突符号的发射**不由 `using` 列表驱动, 而由模板实例化驱动**: 模块导出
  `basic_regex` / `regex_search` 等模板, 消费者 TU 实例化时其模板体引用这些
  `re_detail_600` helper, GCC 把它们的函数内 static 以**外部链接强符号**发射进
  消费者 TU, 与 regex 库 TU 各自的定义撞车。
- 普通 (非模块) 编译下 GCC 对这些符号给 vague linkage (weak/COMDAT) 合并;
  gcc 模块管线 (`-fmodules`) 下消费者侧以强符号发射 → 多重定义。

### 3.3 尝试方案 B — 定向裁剪 regex 导出 (无效)

- 从 `regex.inc` 注释掉 4 个冲突 `using` 实体
  (`get_default_class_id` / `get_default_error_string` / `lookup_default_collate_name` / `mem_block_cache`)。
- clean 重建 (`mcpp clean` + `touch src/regex.cppm` 规避无 depfile 的 stale BMI) 后仍失败;
  `nm` 证实消费者 `regex.o` 依旧发射这些符号。
- **结论**: 模板可达性路径不受 `using` 列表控制, 裁剪导出无法阻止消费者发射 → B 无效, 已回退。

### 3.4 尝试方案 A — 换系统 gcc (无效)

- 假设: M4 文档称 gcc/mingw 28/28 绿, 可能是用系统 scoop gcc (MinGW-Builds
  posix-seh) 而非 xim winlibs (ucrt) 验的。
- 做法: 备份后把 mcpp gcc 16.1.0 payload 整体替换为系统 scoop gcc
  (x86_64-posix-seh-rev1 16.1.0), 并补齐其 std 模块源
  (`include/c++/16.1.0/bits/std.cc`, scoop 的 C++ 头在 `lib/gcc/.../include/c++/`,
  与 xim 布局不同), `mcpp test regex --no-cache` 全量真实构建。
- 结果: **同样失败, 冲突符号与 xim gcc 完全一致**; 两构建的 nm 输出逐符号相同。
- **结论**: 与 gcc 具体发行版 (ucrt/posix-seh) 无关, 是 **gcc 16.1.0 模块管线
  本身行为**。

## 4. B' 方案实施 (本轮) — 切断静态发射路径

B' 定义: 不只动 `using` 列表, 而是**让消费者不再发射冲突的函数内 static** —
两个手段:
1. **内部链接化**: 把只读数据从函数内 static 改为命名空间作用域 `static`
   (内部链接), 消费者 TU 发射 LOCAL 符号, 与库 TU 不可能撞车;
2. **外移定义**: 把带函数内 static (且无法内部链接化) 的成员函数定义移入编译库 TU,
   头文件只留声明, 消费者一律外部调用。

### 4.1 根因精确定位 (llvm-readobj 佐证)

§3.2 的 "强符号" 描述修正为段级事实:

- 消费者 TU (`regex.o`) 中, **函数本体在 COMDAT 段** (LINK_ONCE_DISCARD, 可合并),
  但**函数内 static 落在普通段** (`.data`/`.rdata`/`.bss`, `scl 2` External);
- 库 TU (`posix_api.o` 等) 中同一 static 在命名 COMDAT 段 `.data$_ZZ...` → ld
  对普通段强符号 + COMDAT 副本报 multiple definition。
- 模板的局部 static 同样受害: 真实构建里 `get_default_class_id<char>::data/ranges`
  在普通 `.rdata` (独立复现中模板 static 为 COMDAT, 触发差异未识别 — 不影响结论)。

### 4.2 独立复现实验与候选修复评估

用 gcc 16.1.0 + `-fmodules` + `gcm.cache` 搭最小工程 (hdr.hpp + mod.cppm +
consumer.cpp + libside.cpp, `export using` 同本仓库方案), 逐项验证:

| 候选 | 结果 |
|---|---|
| 非模板 inline 函数局部 static → 消费者发射 `D` 强符号普通段 | **复现** (与真实构建一致) |
| 函数加 `__attribute__((weak))` | **无效** (static 仍强符号; 且 GCC 警告 inline+weak) |
| 局部变量加 `__attribute__((weak))` | 编译拒绝 (`weak declaration of 's' must be public`) |
| 命名空间作用域 `static` (内部链接) | **有效**: 消费者发射 LOCAL 符号 (`b _ZN...L9leaf_fn_sE`), 链接通过 |
| 模板函数局部 static | 复现中为 COMDAT 无冲突 (真实构建却普通段 — 差异未识别) |
| 类模板静态成员 (非匿名命名空间) | **有效**: COMDAT, 消费者/库 TU 合并正常 |
| 匿名命名空间类模板静态成员 | **GCC ICE** (gimplify_expr 段错误) — 弃用 |
| 局部类 static 数据成员 (C++23) | GCC 16 在模板内拒绝 (`-Wtemplate-body`) — 弃用 (§5 url 宏方案因此死路) |

结论: **内部链接命名空间 `static` + 类模板静态成员** 是唯一稳妥的头部内方案。

### 4.3 regex 修复 (vendored 头, 均带 `M5 B'` 注释)

`deps/boost/boost/regex/v5/`:

- **regex_traits_defaults.hpp**:
  - `get_default_error_string` 的 `s_default_error_messages` →
    命名空间作用域 `static const char* const[]` (函数体只做下标访问);
  - `lookup_default_collate_name` 的 `def_coll_names` / `def_multi_coll` → 同上;
  - `get_default_class_id` 的 `data[73]` / `ranges[21]` →
    新类模板 `default_class_id_data<charT>` 的静态成员 (非匿名命名空间, 规避 ICE);
- **mem_block_cache.hpp** (lock-free 与 lock-based 两个变体):
  - `block_cache` → 命名空间作用域 `static mem_block_cache`;
  - `instance()` 定义**移出类体** (类内成员体看不到其后声明的命名空间对象,
    首次内联版编译报 `use of undeclared identifier`)。

### 4.4 boost.system 同模式修复 (full suite 暴露, 基线确认 pre-existing)

同样的 static 模式出现在 boost.system 头 (system/filesystem 测试挂):

- **error_code.hpp** `location()::loc` (`BOOST_STATIC_CONSTEXPR source_location`)
  → 命名空间作用域 `static constexpr source_location default_location` (内部链接);
- **error_category_impl.hpp** `init_stdcat()::mx_` 与
  `operator std::error_category const&() const` 的 `generic_instance`/`system_instance`
  — 后两者构造依赖 `this`, **无法内部链接化** → 定义外移:
  - 头文件只留类内声明 (类本已声明二者, error_category.hpp:141/144);
  - 新增编译库 TU **`src/boost_system_extras.cpp`** (mcpp.toml sources +1 行),
    内含两个定义 (函数内 static 只在此单份存在, 语义不变)。

### 4.5 验证结果 (gcc/mingw clean 全量重建)

- `mcpp test` → **25/28**: regex/system/filesystem 转绿, 其余 21 个原有绿保持;
- llvm/msvc 默认风味 → 28/28 绿; examples 三节全过 (改动两风味共用, 无回归);
- 符号核验: 消费者 `regex.o` 中冲突符号已消失或变 LOCAL/COMDAT
  (`default_class_id_data<char>::data` 进 COMDAT; `s_default_error_messages` 变
  `_ZN5boost13re_detail_600L24...E` 内部链接; `block_cache` 不再发射)。

## 5. 未能解决: gcc/mingw 剩余 3 项 (均为基线既有, 与 regex 无关)

| 测试 | 成因 | B' 为何无效 / 出路 |
|---|---|---|
| **url** | 同一 static 模式, 但 39 处冲突全部来自宏 `BOOST_URL_RETURN_EC` (url/detail/config.hpp:151) 在模板/lambda 内展开的 `static constexpr auto loc##__LINE__` | 宏必须按调用点唯一命名, 无法改命名空间级; 局部类 static 被 GCC 16 拒绝 (4.2)。需宏重构 (如改用 C++20 之后的常量求值路径) 或规则模板整体外移 — 超出 B' |
| **thread** | **另一类 GCC 模块 bug**: `boost::exception_detail::clone_impl<T>` (含 virtual 基类) 的 vtable 在消费者 TU 发射, 但**虚拟 thunk 缺失** (`undefined reference to virtual thunk to ...::clone()/rethrow()/~clone_impl()`, 涉及 broken_promise/unknown_exception/std_exception_ptr_wrapper) | 非 static 问题; 显式实例化可提供 thunk 符号但需枚举所有异常类型, 不稳妥; 等 GCC 修复 |
| **variant** | **GCC 16.1.0 编译器 ICE** (Segmentation fault, boost/variant/detail/has_result_type.hpp:25) | 编译器缺陷, B' 不可解; 等 GCC 修复或换风味 |

## 6. 环境复原

- 全局 `mcpp` 默认 toolchain 恢复为 `llvm@22.1.8` → `x86_64-windows-msvc`。
- 注意: 调查期间 `config.toml` 的 default 多次**自动跳回 llvm** (mcpp 自身行为);
  每次 gcc 验证需先 `mcpp toolchain default gcc --target x86_64-windows-gnu`,
  并核对输出首行 `Resolved gcc@16.1.0 → x86_64-windows-gnu`。
- gcc 16.1.0 payload 保持原 xim winlibs (ucrt) 版未动; 临时复现工程已清理。
- vendored 头改动可回退: 重跑 `uv run scripts/import_boost.py` 即还原上游原貌
  (新文件 `src/boost_system_extras.cpp` 需手动删除)。

## 7. 结论

- M5 达成: 汇总模块 + 示例项目 + 双风味验证框架; B' 修复落地 (regex/system/filesystem
  在 gcc/mingw 转绿), 无 llvm/msvc 回归。
- gcc/mingw 未全绿部分 (url/thread/variant, 全部基线既有) 明确为 gcc 16.1.0 模块管线
  缺陷与编译器 ICE, 与 M5 改动无关 — 移交 M6 CI 阶段修复与回归。
