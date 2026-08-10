# M3 设计: 纯头库模块层 (19 库) + mcpp 构建

> 日期: 2026-08-10 · 状态: 已确认 · 计划: boost-mcpp-module-plan.md M3
> 前置: M0 spike (导出写法/gcc 坑) + M1 vendoring + M2 生成器 (27 库 .inc + 草稿 .cppm)

## 1. 目标与交付物

| 产物 | 说明 |
|---|---|
| `mcpp.toml` | [package] boost/1.91.0 + [build] + [targets.boost] kind="lib" |
| `src/*.cppm` ×19 | M2 草稿定稿 (手编, 见 §3) |
| `src/gen_exports/*.inc` ×19 | 生成器第三轮修复后重新生成 (见 §4) |
| `src/core.cppm` | 对象宏 re-homing: `boost::BOOST_VERSION` / `boost::BOOST_LIB_VERSION` constexpr |
| `include/boost-module/macros.hpp` | 宏拼写旁路头 (M0 §5 模式) |
| `tests/*.cpp` ×20 | 19 库 smoke + macros 旁路头测试 |
| `scripts/curated/any.txt` | curated 机制首个实例 (typeindex 兜底) |
| `scripts/{gen_exports,boost_common}.py` | 第三轮修复 (生成器缺陷) |

## 2. 构建配置 (mcpp.toml)

- 默认工具链: llvm 22.1.8 / x86_64-windows-msvc (mcpp 本机默认) — **与 M2 生成快照 (mingw
  风味) 不同, 由 .inc 守卫兼容 (见 §5)**
- `[build]`: sources = 19 个 .cppm (M4 的 8 库留在 src/ 但不在 sources);
  include_dirs = ["include", "deps/boost"] (旁路头 + vendored 汇总根, 传播给消费者);
  defines = ["BOOST_ALL_NO_LIB"]; cxxflags = ["-w"]
- gcc 风味验证: `mcpp build --target x86_64-windows-gnu` 通过

## 3. 模块定稿 (.cppm)

- 每个 .cppm: `module;` + GMF include 集 (M2 gate 裁剪结果) + `export module boost.X;`
  + `export import` (来自 *.deps) + `#include "gen_exports/X.inc"`
- 三处手编偏离生成草稿 (均有注释):
  1. **core.cppm**: 追加 re-homed 宏 constexpr 块
  2. **scope.cppm**: 移除 `export import boost.core;` — gcc 16.1.0 对此 GMF 集 +
     re-export core 组合 ICE (Segmentation fault at export-module 行, 已二分定位:
     defer+checker+fail+success+unique_fd 5 头 + export import 触发); scope.inc 无
     core 实体, 消费者自 import boost.core
  3. **algorithm.cppm**: string_regex.hpp → string.hpp 聚合头 — gcc 16.1.0 对 regex v5
     abi-tag 表面在模块接口内报 "mismatching abi tags for get_catalog_name_inst"
     (普通编译正常, 模块导出上下文触发); 同步裁剪 algorithm.inc 的 *regex 实体
     (29 行)。clang 风味不受影响 (M4 regex 接入时重新评估)
- 18 库的 export import 链与 M2 .deps 一致

## 4. 生成器第三轮修复 (M2 产物缺陷, M3 落地)

libclang 解析缺陷导致一批 API 面丢失, 全部在本里程碑修复并重新生成 19 库 .inc:

1. **libclang 资源目录缺失**: Windows 下 libclang.dll 找不到自带资源目录
   (mm_malloc.h) → mingw <malloc.h> include 链断 → std 头损坏 → 引用 std::size_t 的
   声明静默丢失 (mp11 的 mp_at_c/mp_iota_c 全部消失)。**修复**: boost_common.py 在
   load_libclang 后从 dll 位置探测 `lib/clang/<ver>/include` 追加到 CLANG_ARGS;
   pip 的 libclang wheel 无资源目录 → 需 LIBCLANG_PATH 指向完整 LLVM 安装
   (README 已有指引)。libclang 22.1.8 + 资源目录后 mp11 实体 239 → 457
2. **using-injection 未收集**: boost 用 `using boost::range_adl_barrier::count;`
   (相对限定 `using range::count;` 在 namespace boost 内) 和
   `using namespace range_adl_barrier;` 两种形式把实体注入公共拼写 (boost::count 等);
   生成器只收集声明实体, 注入名全部丢失 (range 224 → 337, iterator 335 → 400,
   algorithm 545 → 630)。**修复**: collect_injections 按 token 流解析 using-decl /
   using-directive, 注入名作为独立记录输出 (GMF 可见性由 include-DAG 保证)
3. **CLASS_TEMPLATE 未收集**: EXPORT_KINDS 缺 CLASS_TEMPLATE — 类模板主模板从不被
   直接收集 (此前经闭包/部分特化间接进入, 平台分支下会漏 — type_traits 的 is_integral
   主模板整个丢失)。**修复**: 加入 EXPORT_KINDS (optional 37 → 311, 全 19 库实体数
   大幅补全)
4. **typedef linkage 误杀**: typedef/别名无链接概念 (libclang 报 NO_LINKAGE),
   linkage_ok 一律拒绝 → endian 的 big_uint16_t 等全丢。**修复**: 这两类跳过链接检查
   (endian 78 → 235)
5. **using-directive 无 USR**: build_usr_index 的 `if usr` 过滤掉 USING_DIRECTIVE
   (clang 不给 USR) → 位置回退 key
6. **curated 读取落地** (M2 §2.3 承诺): scripts/curated/<lib>.txt 每行一个限定名,
   与注入记录同构输出。首个实例 curated/any.txt — any_cast 函数体引用 typeindex 系
   (闭包只走声明 + canonical 把 type_info 消解成 std::type_info, 均不可达)
7. **闭包 canonical 消解**: 记录为已知限制 — boost 命名空间别名到 std 的实体
   (type_info 等) 需 curated 兜底

## 5. 平台差异守卫 (.inc 内手编 #if)

生成快照 = mingw 风味 (__GNUC__ 定义), 构建在 llvm/msvc 风味 (无 __GNUC__) →
6 处差异实体用 `#if` 守卫兼容 (每处均有注释, 重新生成后需重补 — 已知代价):

| 位置 | 实体 | 条件 |
|---|---|---|
| core.inc | boost::core::detail::copysign_impl | `__GNUC__` (cmath.hpp 分支) |
| core.inc | boost::int128_type / uint128_type | `BOOST_HAS_INT128` (suffix.hpp, MSVC ABI 无 __int128) |
| variant.inc | mpl::aux::arity_helper / arity_tag / max_arity / nested_type_wknd / template_arity_impl | `__GNUC__` (mpl gcc-preprocessed 目录) |
| mp11.inc | detail::mpmf_unwrap / mpmf_wrap | 非 gcc (gcc ≥ 14 走 mp_map_find_impl 分支, gcc bug 120161) |
| tuple.inc | detail::ignore_t | 非 gcc (成员指针 typedef, gcc 判内部链接) |
| any.inc | int128_type / uint128_type | `BOOST_HAS_INT128` |

## 6. 对象宏 re-homing 与旁路头

- **模块面**: core.cppm 导出 `namespace boost { constexpr int BOOST_VERSION = 109100;
  constexpr const char* BOOST_LIB_VERSION = "1_91"; }` (拼写保持)。值手工与
  deps/boost/boost/version.hpp 对齐, tests/core.cpp static_assert 校验
- **宏面**: include/boost-module/macros.hpp → `#include <boost/version.hpp>`。
  约束: 与模块 GMF include 集不相交 (version.hpp 未被任何 M3 模块 GMF 包含, M0 §5)
- **互斥**: 同一 TU 内宏定义会吞掉 boost::BOOST_VERSION 拼写 (宏展开 → boost::109100),
  两种拼写二选一 — tests/macros.cpp 用宏面, tests/core.cpp 用模块面

## 7. 验证结果

- **llvm 22.1.8 / x86_64-windows-msvc (mcpp 默认)**: 19 模块构建 ✓, 20 测试全绿
  (tests/core.cpp 内含 BOOST_VERSION static_assert; tests/macros.cpp 验证旁路头;
  scope_exit.cpp 验证宏库混合模式)
- **gcc 16.1.0 / x86_64-windows-gnu**: 19 模块构建 ✓ (scope/algorithm 变通后),
  测试 19/20 — variant 消费者编译触发 gcc 16.1.0 ICE (has_result_type.hpp,
  编译器 bug, 已随 M2 冒烟记录同类先例)
- 测试覆盖面: 每库典型 API (类模板跨模块实例化、自由运算符、ADL、异常、流 I/O、
  mp11 元函数、range adaptor 函数形式等)

## 8. 已知限制 (M3 边界)

- **匿名命名空间 forwarder 不导出** (标准限制): range adaptors 的
  reversed/filtered/transformed 是匿名命名空间 const 对象, 模块无法导出 —
  消费者用函数形式 reverse/filter/transform (pipe 语法不可用)
- **gcc 16.1.0 模块 ICE**: scope 模块构建 (已绕过)、variant 消费者 (挂起, 无解 —
  gcc 模块实现缺陷, 建议 CI 的 gcc 风味排除 variant 测试或整体以 clang 为准)
- **gcc algorithm 模块无 regex 面** (abi-tag 冲突, §3.3)
- **.inc 守卫重生成会丢失**: 重新运行 gen_exports.py 后须按 §5 表重补
- **range 的 boost::distance 注入名归 iterator 模块** (first-wins) — 消费者需
  import boost.range 连带 export-import 链 (range.cppm export import iterator ✓)
