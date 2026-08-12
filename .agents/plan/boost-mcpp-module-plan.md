# Boost 1.91.0 C++23 模块封装计划（仿 opencv-m）

> 日期: 2026-08-08 · 状态: 已确认 · 目标上游: Boost 1.91.0 (BOOST_VERSION 109100)
> 前置调研: deps/boost 为 git superproject 子模块检出, 缺顶层 `boost/` 汇总 include 根 (被 .gitignore 排除),
> 需改为从官方 boost-1.91.0.tar.gz 导入 (M1)。树内实测: 157 libs / 17322 .hpp / 16270 .cpp;
> 全树 `static inline` 3440 处但集中在 macro 系库, 目标核心库实测为 0 (optional/variant/any/core/mp11/filesystem/regex/algorithm 等)。

## 目标

包定义: `[package] namespace="boost", name="boost", version="1.91.0"`, 单仓库承载 vendored 源码 + 模块层 + 完整构建。
消费者 `import boost.filesystem;`(或汇总 `import boost;`), API 拼写与上游一致, 不 include 头文件。

## 仓库布局

```
boost-module/                       # = mcpp 包仓库
├── mcpp.toml                       # [package] + [build].sources/include_dirs + [targets.boost] kind="lib"
├── src/
│   ├── boost.cppm                  # 汇总模块: export import 全部子模块
│   ├── optional.cppm / variant.cppm / ...   # 每库一个
│   ├── gen_exports/*.inc           # 生成器产物 (committed)
│   └── *_fns.inc                   # 手工替代文件 (目标库 static-inline≈0, 预计极少)
├── include/boost-module/macros.hpp # 宏旁路头: BOOST_VERSION 等, 消费者 import 前 include
├── deps/boost/                     # vendored 1.91.0, 含 boost/ 汇总根 (M1 重做)
├── scripts/                         # 脚本统一放这里
│   ├── import_boost.py              # 下载(固定 sha256) + 选择性导入 + 裁剪, 落位 deps/boost/
│   ├── gen_exports.py               # libclang AST 枚举 + 依赖闭包
│   ├── gen_audit.py                 # static-inline/内部链接审计
│   └── curated/<mod>.txt            # 生成器看不见的兜底清单
├── tests/                          # 每库 smoke test (mcpp workspace)
├── examples/                       # import boost; 示例项目
├── docs/architecture.md
└── .github/workflows/ci.yml        # win/mac/linux 矩阵
```

## 里程碑

### M0 — Spike 验证 ✅ 已完成 (2026-08-08)
详见 [2026-08-08-m0-spike-results.md](2026-08-08-m0-spike-results.md)。
4 探针 (optional/mp11/container/filesystem) 在 clang 22 + gcc 16 双编译器全过。核心结论:
- opencv 式 `export namespace boost { using ...; }` 成立; 自由运算符须显式 using, friend 运算符靠 ADL
- gcc 需为 GMF 全局辅助实体补 `export using ::operator new;` (container placement_new 实例)
- 消费者 std 表面: clang 可 include; gcc 用 `import std;` (`--compile-std-module` 预编译一次) 或 header unit 后备
- 编译库声明/定义链接模式成立 (filesystem 10 cpp 验证)
- 后续里程碑按此结论推进, 生成器规则见报告第 7 节

### M1 — Vendoring 重做 ✅ 计划调整 (2026-08-09)
原方案 (scripts/vendor/import_boost.ps1 + scripts/clean-boost.ps1) 调整为用户指定的实现:
**`scripts/import_boost.py` 单脚本完成全部工作**, `scripts/clean-boost.ps1` 删除。

> **源码布局来龙去脉 (防后续 Agent 重复踩坑)**:
> 最初仓库用的是 GitHub 源码包, 其头文件分散在 `libs/<lib>/include/boost/...` (superproject 检出,
> 且缺顶层 `boost/` 汇总 include 根, 被 .gitignore 排除 — M0 只能拼 161 个 libs 路径作联合 include)。
> M1 改用官方 release tarball (archives.boost.io) 后**布局完全不同**: 所有库的头文件统一收在
> 顶层 **`boost/boost/` 汇总 include 根**下 (`boost/optional.hpp`、`boost/filesystem/...` 都在这里),
> `libs/<lib>/` 下**没有** `include/` 目录, 只保留 CMakeLists.txt / meta / test 等构建元数据。
> 因此 **deps/boost/boost/ 才是唯一 include 根** (消费者 `-I deps/boost`), 库与头文件的对应关系
> 需通过 `libs/<lib>/meta/libraries.json` 的 headers 字段或 `boost/` 下同名目录/单头推断
> (M2 生成器输入, 详见 M2 设计文档)。当前 deps/boost 落盘结构即为此布局, 勿再按 libs/*/include 找头。
- 固定源: https://archives.boost.io/release/1.91.0/source/boost_1_91_0.tar.gz
  SHA256=5734305f40a76c30f951c9abd409a45a2a19fb546efe4162119250bbe4d3a463
- 压缩包落位 target/vendor-import/ (已存在, 校验通过)
- 每次运行: 删除旧 deps/boost/ → 校验 sha256 → 选择性解压导入:
  - 导入: boost/ 汇总 include 根 (关键, 修复 M0 缺根问题) + libs/ (裁剪后) + tools/cmake + CMakeLists.txt + LICENSE_1_0.txt + README.md
  - 裁剪规则沿用 clean-boost.ps1 语义: 任意深度的 doc/docs/example/examples/more/status/.github 等目录、
    Jamfile 系文件、*.htm/*.html、根级图片样式文件一律不导入

### M2 — 生成器 scripts/gen_exports.py ✅ 已完成 (2026-08-09)
libclang AST dump 目标库公共头 → 收集 boost:: 外部链接实体;
依赖闭包 (filesystem 连带导出 boost::system::error_code — opencv-m dependency-closure 先例);
跨模块去重 (first wins); 产出 export using 列表 (写法以 M0 验证结果为准)。
gen_audit.py 输出需手工替代的 static-inline 清单。

> 实现与关键差异详见 [2026-08-09-m2-gen-exports-design.md](../docs/2026-08-09-m2-gen-exports-design.md) §10/§11:
> - 产出: scripts/{gen_exports,gen_audit,boost_common}.py + scripts/libs.json (root 头集, 938 头) +
>   src/gen_exports/*.inc (27 库 4009 实体) + *.deps (export-import 提示) + src/*.cppm 草稿 (M3 定稿)
> - GMF = include-DAG 源点聚合头 (detail 不自足, 必须走 umbrella; 顺序由上游聚合保证);
>   clang 构建不用 -fmodules (mingw 双重包含); draft .cppm 无 module :private (gcc 未实现)
> - 编译正确性由 clang++ 驱动 gate 保证 (libclang 缺失头报告不可靠), 失败自动裁剪 GFM
>   (thread 平台头、regex ICU 头、json src.hpp 保留等, 详见 §11)
> - 审计: static=6 (thread 1 + json 5, 模块 TU 内部辅助), M3 19 库为 0
> - 冒烟: 27/27 模块 clang 预编译通过; optional/system/algorithm/json 消费者运行通过;
>   gcc 模块构建通过 (消费者 std 表面按 M0 §2 用 import std; 路径)

### M3 — 纯头库模块层 (19 库) ✅ 已完成 (2026-08-10)
optional / variant / variant2 / any / core / container_hash / mp11 / static_string / scope /
scope_exit / type_traits / algorithm / iterator / range / io / rational / endian / tuple / system。
对象宏 re-homing (BOOST_VERSION → boost:: constexpr 保持拼写); include/boost-module/macros.hpp 旁路头;
每库 smoke 测试; 跑通 mcpp build/test。

> 实现与差异详见 [2026-08-10-m3-header-only-modules.md](../docs/2026-08-10-m3-header-only-modules.md):
> - 生成器第三轮修复: libclang 资源目录 (mp11 mp_at_c 修复, 239→457 实体)、using-injection/
>   directive 收集 (range 224→337 等)、CLASS_TEMPLATE 收集 (optional 37→311)、typedef
>   linkage 放宽 (endian 78→235)、curated 读取落地 (curated/any.txt typeindex 兜底)
> - mcpp.toml: sources=19 .cppm, include_dirs=include+deps/boost, llvm/msvc 默认风味
>   (生成快照 mingw 风味由 .inc 6 处 #if 守卫兼容)
> - 对象宏 re-homing 于 boost.core; macros.hpp 旁路头; 两种拼写同 TU 互斥 (宏吞拼写)
> - 手编偏离: scope.cppm 去 export import core (gcc ICE)、algorithm.cppm 去 string_regex
>   (gcc abi-tag, 剪 *regex 实体)
> - 验证: llvm/msvc 20/20 测试绿; gcc 构建绿 + 19/20 (variant 消费者 gcc ICE, 编译器 bug)

### M4 — 编译库接入 (8 库) ✅ 已完成 (2026-08-11)
filesystem / regex / thread / chrono / program_options / stacktrace / json / url。
libs/*/src/*.cpp 进 sources, 统一 -DBOOST_ALL_NO_LIB (关 MSVC autolink), -w 压告警;
模块 TU 与库 TU 宏一致 (opencv BMI 基线标志教训); json/url 编译策略按库实际定。

> 实现与差异详见 [2026-08-11-m4-compiled-libs.md](../docs/2026-08-11-m4-compiled-libs.md):
> - 8 库 .inc 为 M2-era 快照 (缺 M3 生成器修复) → 27 库全量重生成, 实体归属随 first-wins 变动
> - 生成器增强: EXTRA_DEFINES (stacktrace LINK 面)、GMF_OVERRIDE (json 去 src.hpp 后快照同构)、
>   curated 升级为跨模块覆盖 (any_cast 模板体需 typeindex 运算符, 被 first-wins 判给 variant)
> - curated/filesystem.txt: iterator_facade 类内 friend 运算符模板对消费者 ADL 不可见 → 模块面再导出
> - scripts/reapply_hand_edits.py: 重生成后一键重放全部 M3/M4 手编 (幂等)
> - mcpp.toml: 27 .cppm + 52 库 TU; defines 补 _MT / _WIN32_WINNT=0x0A00; per-glob
>   BOOST_THREAD_BUILD_LIB (tss_cleanup_implemented); 线程源码按平台互斥
> - 验证: llvm/msvc + gcc/mingw 双风味 28/28 测试全绿 (M3 遗留 variant gcc ICE 不再触发)
>   **修订 (M5)**: "gcc/mingw 28/28 全绿" 记录不实 — M5 full suite 实为 5 项失败
>   (system/filesystem/url/thread/variant), 疑当时未真正跑 gcc 全量; 前二者同 static 模式
>   已由 M5 B' 修复, 后三者移交 M6 CI (见 M5 设计文档 §5)

### M5 — 汇总模块与消费者验证 ✅ 已完成 (2026-08-12)
src/boost.cppm 汇总 (`export import` 27 子模块); examples/ 示例项目 — 按用户指定不用
`mcpp new`, 直接建 `mcpp.toml` + 源文件, `[dependencies] boost.boost = { path = ".." }`;
`import boost;` 跑 filesystem 读写 + json 序列化 + regex 匹配。
另实施 **B' 方案**修复 gcc/mingw 模块链接多重定义 (regex/system/filesystem)。

> 实现与差异详见 [2026-08-12-m5-aggregate-consumer.md](../docs/2026-08-12-m5-aggregate-consumer.md):
> - 根因: gcc 16.1.0 模块管线在消费者 TU 把 inline 函数内 static 以强符号落普通段
>   (函数本体 COMDAT 可合并), 与库 TU 的 COMDAT 副本多重定义; 发射由模板可达性驱动,
>   不受 export using 列表控制 (方案 B 裁剪无效)
> - B' 两手段: 内部链接化 (命名空间级 static / 类模板静态成员) + 外移定义
>   (boost.system 两成员函数 → 新库 TU src/boost_system_extras.cpp)
> - 验证: llvm/msvc 28/28 绿 + 示例全过; gcc/mingw 25/28 — regex/system/filesystem 已解,
>   url/thread/variant 为基线既有失败 (另一类 GCC 模块 bug 与编译器 ICE), **移交 M6 CI 适配**
> - 修订: M4 记录 "gcc/mingw 双风味 28/28 全绿" 不实 — 本轮 full suite 实为 5 项失败

### M6 — CI 与发布
三平台 Actions 矩阵; **gcc/mingw 纳入 CI 门禁并完成适配** — M5 移交的三项基线失败
(url: BOOST_URL_RETURN_EC 宏静态冲突 / thread: clone_impl 虚拟 thunk 缺失 / variant: gcc ICE)
在此修复并全量回归 (含 M5 B' 改动回归验证); mcpp-index 薄层 boost.lua 指向 release;
docs/architecture.md。

## 边界与已知限制

- macro 驱动库不封装: preprocessor/mpl/fusion/proto/spirit/xpressive/lambda/bind/typeof 等保持 include 用法
  (标准允许 import+include 混合)
- 特性宏构建期固定: 消费者无法自定义 BOOST_* 特性宏 (asio/locale/log/context 等留后续 feature 里程碑)
- context/coroutine/fiber 带 asm, mpi/python/locale(ICU) 有外部依赖: 明确排除在首发外
- 模块接口 TU 不能带非基线编译标志 (opencv -msse3 教训); boost 无特殊 ISA 需求, 风险低

## 工作量预估

M0–M3 核心管线 2–3 天; M4 2–3 天; M5–M6 1–2 天。
