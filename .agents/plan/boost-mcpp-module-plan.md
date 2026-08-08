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
├── tools/
│   ├── vendor/import_boost.ps1     # 固定 sha256 + 调用 clean-boost.ps1
│   ├── gen_exports.py              # libclang AST 枚举 + 依赖闭包
│   ├── gen_audit.py                # static-inline/内部链接审计
│   └── curated/<mod>.txt           # 生成器看不见的兜底清单
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

### M1 — Vendoring 重做
当前 deps/boost 缺顶层 boost/ 根 (b2 headers 产物, 被 gitignore)。改从官方 tarball 导入:
tools/vendor/import_boost.ps1: 下载 boost-1.91.0.tar.gz (固定 sha256, GitHub/gitcode 双镜像仿 import_opencv.sh),
解压后保留 libs/ + boost/ + tools/cmake + LICENSE_1_0.txt + CMakeLists.txt, 再跑 script/clean-boost.ps1 -Force。
提交 boost/ 根, 修正 .gitignore。

### M2 — 生成器 tools/gen_exports.py
libclang AST dump 目标库公共头 → 收集 boost:: 外部链接实体;
依赖闭包 (filesystem 连带导出 boost::system::error_code — opencv-m dependency-closure 先例);
跨模块去重 (first wins); 产出 export using 列表 (写法以 M0 验证结果为准)。
gen_audit.py 输出需手工替代的 static-inline 清单。

### M3 — 纯头库模块层 (19 库)
optional / variant / variant2 / any / core / container_hash / mp11 / static_string / scope /
scope_exit / type_traits / algorithm / iterator / range / io / rational / endian / tuple / system。
对象宏 re-homing (BOOST_VERSION → boost:: constexpr 保持拼写); include/boost-module/macros.hpp 旁路头;
每库 smoke 测试; 跑通 mcpp build/test。

### M4 — 编译库接入 (8 库)
filesystem / regex / thread / chrono / program_options / stacktrace / json / url。
libs/*/src/*.cpp 进 sources, 统一 -DBOOST_ALL_NO_LIB (关 MSVC autolink), -w 压告警;
模块 TU 与库 TU 宏一致 (opencv BMI 基线标志教训); json/url 编译策略按库实际定。

### M5 — 汇总模块与消费者验证
src/boost.cppm 汇总; mcpp new 示例项目依赖本包, import boost; 跑 filesystem 读写 + json 序列化 + regex 匹配。

### M6 — CI 与发布
三平台 Actions 矩阵; mcpp-index 薄层 boost.lua 指向 release; docs/architecture.md。

## 边界与已知限制

- macro 驱动库不封装: preprocessor/mpl/fusion/proto/spirit/xpressive/lambda/bind/typeof 等保持 include 用法
  (标准允许 import+include 混合)
- 特性宏构建期固定: 消费者无法自定义 BOOST_* 特性宏 (asio/locale/log/context 等留后续 feature 里程碑)
- context/coroutine/fiber 带 asm, mpi/python/locale(ICU) 有外部依赖: 明确排除在首发外
- 模块接口 TU 不能带非基线编译标志 (opencv -msse3 教训); boost 无特殊 ISA 需求, 风险低

## 工作量预估

M0–M3 核心管线 2–3 天; M4 2–3 天; M5–M6 1–2 天。
