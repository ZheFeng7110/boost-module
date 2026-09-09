# boost-module 架构文档

> 日期: 2026-09-09 · 面向消费者 · 内容抽取自
> [总体设计汇总](../.agents/docs/2026-09-08-consolidated-design.md) (权威口径以该文档为准)
> 目标上游: **Boost 1.91.0** (`BOOST_VERSION 109100`)

## 1. 项目定位

使用 [mcpp](https://github.com/mcpp-community/mcpp) 构建工具对 Boost 库做 C++23
named modules 封装: 把 Boost 的头文件 API 以模块接口 (`.cppm` +
`export namespace boost { using ...; }`) 形式导出, 消费者可以
`import boost.filesystem;` (或汇总 `import boost;`), API 拼写与上游一致,
无需 `#include` 头文件。

- **规模** (2026-09-09 C5 后): 116 个模块接口 / 118 个 feature (含 log、
  unit_test_framework 两个无模块 feature) / 默认 49 库闭包 /
  封装可消费总数 138 库 (116 模块 + 2 编译库 include-only + 20 纯 include-only)。
- **平台**: CI 四腿覆盖 windows (clang-msvc) / linux (gcc 16, llvm) / macos
  (llvm, arm64)。mingw 与真 MSVC (cl) 不承诺 (见 §5 支持矩阵)。
- **许可**: 封装层 BSL; Boost 上游 BSL; libclang Apache-2.0-LLVM。

## 2. import 用法

### 2.1 依赖声明 (git dep)

```toml
# 默认: 49 库闭包
[dependencies]
boost.boost = { git = "https://github.com/ZheFeng7110/boost-module", tag = "b1.91.0w0.0.0-prelease" }

# 只选若干库 (default-features = false 关闭默认集)
[dependencies.boost.boost]
git = "https://github.com/ZheFeng7110/boost-module"
tag = "b1.91.0w0.0.0-prelease"
default-features = false
features = ["optional", "json"]

# 全量
boost.boost = { git = "https://github.com/ZheFeng7110/boost-module", tag = "b1.91.0w0.0.0-prelease", features = ["all"] }
```

后续正式版发布后会上架 mcpp package，现阶段先使用 git 依赖。

> **clang 下不要用 `features = ["all"]`**: 全部 117 个 CMI 约 2.98GB, 超过
> clang 2^31 源位置上限, 报 "ran out of source locations", 无 flag 可调。
> **全量需求请逐库 import** (用户决策 2026-09-08); gcc 侧同限未实测。

### 2.2 三种消费形态

1. **模块 import** (116 库): `import boost.<lib>;` / `import boost;`。
   `import boost;` 是 build.mcpp 动态生成的汇总模块, 恰好 re-export 当前
   激活的库; 零激活时是合法空壳。API 拼写与上游一致; 自由运算符已显式导出;
   friend 运算符经 ADL。

   ```cpp
   import boost.filesystem;   // 单库
   import boost;              // 汇总 (re-export 当前激活的库)
   ```

2. **纯 include-only** (20 库): 无 feature 无模块, 直接 `#include` 上游头。
   可与模块 import 同 TU 混用 (标准允许)。宏 API
   (BOOST_PP_/BOOST_FOREACH/BOOST_DESCRIBE_*/BOOST_OPENMETHOD*/
   BOOST_SCOPE_EXIT_* 等) 永远只能来自 include —— 宏是预处理器层面的 API,
   不跨模块边界。

   ```cpp
   #include <boost/preprocessor/cat.hpp>   // 宏 API: 只能 include
   #include <boost/foreach.hpp>
   import boost.core;                      // 模块化库照常 import, 两者共存
   ```

3. **编译库 include-only** (2 库: log、test): feature 保留库 TU 编译链接,
   但没有 `export module boost.<lib>;` 模块接口。
   - **log**: `--features log` + `#include <boost/log/...>` + 链接库 TU。
   - **test** (`unit_test_framework`): **双形态消费, 两形态不可同链接**
     (框架 TU 与 included 聚合实现符号冲突, 二选一):

     | 形态 | feature | include | 链接 |
     |---|---|---|---|
     | 编译框架 (官方推荐) | `--features unit_test_framework` | `<boost/test/unit_test.hpp>` (+ `BOOST_TEST_NO_MAIN` + `<boost/test/impl/unit_test_main.ipp>` 取 runner, 或自持 main) | 包内框架 TU |
     | 纯头文件库 (官方可选) | 不启用 | `<boost/test/included/unit_test.hpp>` (聚合头, 自带 main) | 无 |

### 2.3 版本常量 (`boost.version`)

```cpp
import boost.version;    // 默认集内, import boost; 已自动 re-export
static_assert(boost::BOOST_VERSION == 109100);
static_assert(boost::BOOST_LIB_VERSION[0] == '1');
```

宏形式 (`#if BOOST_VERSION >= 109100`) 由消费者自行
`#include <boost/version.hpp>`; **同一 TU 内宏定义与模块拼写互斥**
(宏会展开 `boost::BOOST_VERSION` → `boost::109100`), 二选一。

## 3. feature 选择性构建语义

每个库对应一个 feature (`scripts/gen_features.py` 生成, 勿手改):
116 个模块 feature (T0 26 + T1a 61 + T2 16 + T1b 12 + `version` 1) +
2 个无模块 feature (log、unit_test_framework)。

- **默认集 = 49 库闭包** (`[features].default`, 随模块 import 边自动增长):
  `mcpp build` / `mcpp test` 覆盖核心面 (19 个原核心库 + config/assert/
  utility/move 等基建库 + `boost.version`)。
- **opt-in 库**: 其余 feature 需显式激活, `mcpp build --features <库,...>`;
  消费者 `features = [...]` + `default-features = false`。
- **implies 闭包**: feature 可声明 `implies` (传递闭包), 例如
  `--features log` 会拉齐链接依赖 (log/utf 的 implies 手工钉定,
  `EXTRA_IMPLIES = {"parser": ["charconv"]}`)。
- feature 变化改变 cflags → BMI/构建缓存自动失效;
  `MCPP_FEATURE_<NAME>` 宏仅本包编译期可见 (不传播消费者)。
- 消费者必须自带 std 表面 (`import std;` 或 include) —— boost 实体签名
  引用 std 类型的运算符在纯 import TU 不可见 (设计使然)。

## 4. 已知限制 (消费者须知)

### 4.1 工具链/标准硬限制

| 限制 | 消费方式 |
|---|---|
| clang `--features all` 超 2^31 源位置上限 (~2.98GB CMI) | **推荐逐库 import** (用户决策 2026-09-08); gcc 侧未实测 |
| 特性宏一律构建期固定 | 消费者无法自定义任何 BOOST_* 特性宏 |
| filesystem 固定 v3 API; thread 固定 v2 API (`unique_future`); stacktrace basic | 拼写按对应上游版本 |
| algorithm 无 regex 面 (gcc abi-tag) | regex 需求另行 include 上游头 |
| iostreams 外部后端 (zlib/gzip/bzip2/lzma/zstd) 与 cobalt ssl 不入包 (OpenSSL) | 自备外部依赖 |
| math tr1、container dlmalloc/alloc_lib、process 聚合头不入包 | 用主 API 面 |
| log event_log 手写 mc.exe 桩、dump_avx2/ssse3 不入包 | 平台裁剪 |
| atomic sse41 走探测失败回退 | 自动 |
| type_erasure `any<>` 动态分发路径 clang-msvc 模块消费者不可实例化 | 模块面/概念模板可用 |
| `numeric::interval<double>` 模块面不可实例化 (默认 policies 显式特化) | include 头文件 |
| 匿名命名空间 forwarder 不导出: range pipe 语法 (`vec \| reversed`)、multi_array `boost::extents` | 用函数形式/容器式构造 |
| 内部链接 constexpr 对象不可导出 — 残余面: accumulators `extract::*` (用 `extract_result<>`)、mqtt5 `prop::*` (用 `integral_constant`) | 按替代拼写 |
| libclang 生成盲点: pfr::tuple_size_v、hana int_c 等变量模板缺失 (类模板替代拼写) | 按替代拼写 |

### 4.2 gcc 16.1 缺陷家族与消费三分规则

gcc 16.1 模块实现存在缺陷家族 (详见设计汇总 §6.1): exception CMI
pendings (库已降级 include-only)、variant `apply_visitor` 自由函数 ICE
(用成员版本)、消费者自定义异常 clone_impl thunk 缺失、CMI/GMF 合并冲突等。

**gcc 消费方式三分规则**: ① 正常 import; ② import + 补标准头
(`<new>`/`<typeinfo>`); ③ 纯 include。每接入/消费新库需重新核实 gcc 消费面。

### 4.3 纯 include-only 库名单 (20 库, 无 feature 无模块)

- **T3 宏驱动 (16)**: preprocessor / mpl / fusion / proto / spirit /
  xpressive / typeof / vmd / phoenix / parameter / metaparse /
  function_types / tti / local_function / msm / foreach —— 公共 API 是宏族,
  named modules 永远无法导出。
- **降级 (4)**: exception (gcc 16.1 CMI pendings)、describe / openmethod /
  scope_exit (宏主体 + gcc 16.1 include+import 混用 ODR 重定义)。

### 4.4 M13 暂缓清单 (11 库, 预览版不支持)

外部依赖/asm 库持续暂缓 (用户决策 2026-09-08), 本期零改动:

> context / fiber / coroutine (asm)、locale (ICU)、mpi、python、
> parameter_python、graph_parallel、compute (OpenCL)、mysql / redis (OpenSSL)

## 5. 支持矩阵

| 平台 / 编译器 | 状态 |
|---|---|
| linux + gcc 16.1 | CI 腿 ✅ (受 §4.2 缺陷家族影响, 逐库核实) |
| linux + llvm (clang) | CI 腿 ✅ |
| macos + llvm (clang, arm64) | CI 腿 ✅ (精确异常 catch 受 Mach-O typeinfo 限制, 需 `std::exception` 兜底写法) |
| windows + clang (clang-msvc 风味) | CI 腿 ✅ |
| windows + 真 MSVC (cl) | **从未验证**, 不承诺 |
| windows + mingw gcc | 无 CI 腿, **不承诺** (已知: thread `sleep_for` 挂起、url `BOOST_URL_RETURN_EC` 宏冲突) |

## 6. 辅助脚本

脚本依赖 **libclang** (`scripts/gen_exports.py` / `scripts/gen_audit.py` 用它解析
Boost 头文件的 AST)。未安装 libclang 时需先安装：

```bash
pip install libclang        # 或设置 LIBCLANG_PATH 指向本地 LLVM 的 libclang.dll
```

安装了 [uv](https://docs.astral.sh/uv/) 的用户无需手动安装 —— 脚本带 PEP 723 内联元数据，
`uv run` 会自动创建带 libclang 的临时环境：

```bash
uv run scripts/gen_exports.py --scan                 # 重新生成 scripts/libs.json
uv run scripts/gen_exports.py                        # 生成全部目标库的导出列表
uv run scripts/gen_exports.py --libs optional system --emit-cppm
uv run scripts/reapply_hand_edits.py                 # 重生成后重放手编 (.cppm 偏离 + .inc 平台守卫 + deps/boost vendored 修补)
uv run scripts/gen_features.py                       # 重新生成 mcpp.toml 的 [features] 块 + scripts/features.lst
uv run scripts/gen_audit.py                          # static-inline / 内部链接审计
uv run scripts/import_boost.py                       # 重新导入官方 boost tarball
uv run scripts/reapply_hand_edits.py          # import_boost 会抹掉 vendored 修补, 重跑本脚本回放 (必须!)
```

> 不用 uv 时照常 `python scripts/xxx.py` 运行即可（shebang 保持普通 `#!/usr/bin/env python3`，
> 内联元数据只是注释）。

各脚本职责：

- `scripts/import_boost.py` — 下载固定 SHA-256 的官方 `boost_1_91_0.tar.gz`，裁剪后导入
  `deps/boost/`（`boost/boost/` 汇总 include 根 + `libs/` 等）。
- `scripts/gen_exports.py` — libclang AST 枚举库的公共头 → 收集 `boost::` 外部链接实体 →
  依赖闭包（如 filesystem 连带 system::error_code）→ 跨模块去重（first wins）→ 产出
  `src/gen_exports/<lib>.inc`（`export namespace boost { using ...; }` 列表）、`*.deps`
  （`export import` 提示）、`src/<lib>.cppm` 草稿。
- `scripts/gen_features.py` — 由 `libs.json` + `src/gen_exports/*.deps` 生成
  `mcpp.toml` 的 `[features]` 块（每库一个 feature，`sources` = 该库 `.cppm` + 编译库
  TU globs；log/unit_test_framework 为无模块 feature，仅库 TU，C1；
  `boost.version` 为 LIBS_SPECIAL 形态, 有 `.cppm` 无 TU globs / 无 `.deps`, C5）
  与 `scripts/features.lst`（build.mcpp 消费）。
  默认集 = 49 库闭包，其余 opt-in（`--features <feature>` 显式激活）。
- `scripts/gen_audit.py` — 输出需手工替代的 static-inline / 内部链接实体清单；
  `--macros` 统计各库公共头的宏注入面（M10 T3 include-only 名单的核实输入）。
- `scripts/reapply_hand_edits.py` — 重生成 `.inc`/`.cppm` 后一键重放全部手编
  （core/scope/algorithm 的 gcc 变通、`.inc` 平台守卫、算法头注释约定），幂等。
  字符串补丁以统一 diff 形式存于 `scripts/patchs/<module>.patch`（一个模块一个
  patch 文件），用 `git apply` 应用并以反向 apply 检测实现幂等；`.inc` 平台守卫、
  vendored 新增文件与 "M3 final form" git 恢复仍为脚本内逻辑。
  同时回放 `deps/boost/` 下的 vendored 头修补（M5 B' / M9 / M11 / M12，
  共 22 个修补文件 + 1 个新增文件）—— `import_boost.py` 重新 vendoring 会把
  这些文件还原成上游原貌，重导入后必须重跑本脚本（rollup 文档 §3.7#1）。

## 7. 相关文档

- 使用文档 (消费者用法速查): [`usage.md`](usage.md)
- 总体设计汇总（替代全部旧设计/计划文档）:
  [`.agents/docs/2026-09-08-consolidated-design.md`](../.agents/docs/2026-09-08-consolidated-design.md)
- 发布预览版计划: [`.agents/plan/2026-09-08-release-preview-plan.md`](../.agents/plan/2026-09-08-release-preview-plan.md)
- `boost.version` 模块设计: [`.agents/docs/2026-09-09-boost-version-module.md`](../.agents/docs/2026-09-09-boost-version-module.md)
