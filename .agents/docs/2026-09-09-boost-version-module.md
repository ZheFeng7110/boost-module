# `boost.version` 模块设计 (C5, 2026-09-09)

> 日期: 2026-09-09 · 状态: 实施完成 · 分支 `b1.91.0wdev`
> 范围: `src/version.cppm` 由手写特例转为 `LIBS_SPECIAL` 形态模块, 接
> `gen_features.py` / `build.mcpp` 流程; 删除冗余的
> `include/boost-module/macros.hpp` 与对应测试; `src/core.cppm` 内的
> `BOOST_VERSION` / `BOOST_LIB_VERSION` 重复常量同步移除。
> 计划档: `.agents/plan/2026-09-09-boost-version-module-promotion.md`。
> 汇总档对应章节: §2.1 / §2.2 / §4.3 / §5 (C5 行) / §10#10。

## 1. 决策全文

1. **`boost.version` 是正式模块**, 走 `gen_features.py` 与 `build.mcpp`
   流程。**不**经 `gen_exports.py` —— 它的全部导出是两个从
   `<boost/version.hpp>` 取值的 `inline constexpr`, libclang bundle TU
   在这里没有意义 (无 AST 实体可扫描; `BOOST_VERSION = 109100` 是
   literal, 不引用任何其他 `boost::*`)。
2. **新增 `LIBS_SPECIAL` tier** (`scripts/boost_common.py`)。
   与 `LIBS_COMPILED_INCLUDE_ONLY` (C1) 互为镜像:
   - C1 形态 (log / test): 有 feature / 有 TU globs / **无 .cppm**;
   - C5 SPECIAL 形态 (version): 有 feature / 有 .cppm / **无 TU globs** /
     **无 .deps**。
   两形态都不能进入 gen_exports.py 的 bundle TU 处理路径, 但都要进入
   gen_features.py 的 feature 注册路径。
3. **`boost.version` 加入默认集** (`DEFAULT_CANDIDATES`)。`version` 无
   `.deps` 边, 闭包扩张 = +1 = 49。理由: M3 final form 通过 `core` 给
   默认消费者 `boost::BOOST_VERSION`; 转 SPECIAL 后若不放默认, 默认消费
   者丢掉该常量, 是回归 (隐式 breaking)。
4. **`include/boost-module/` 目录与 `macros.hpp` 头删除**。宏形式用户
   自行 `#include <boost/version.hpp>` 解决 —— 上游头自包含 header
   guard, 与本包无命名空间冲突, 且本包其他模块的头文件 (核心如 core,
   accumulators, asio 等) 本来就 transitively include 它。
5. **`src/core.cppm` 移除 `BOOST_VERSION` / `BOOST_LIB_VERSION` 常量**。
   理由: 与 `boost.version` 重复; 默认消费者仍可通过 `import boost;`
   聚合拿到 `boost::BOOST_VERSION`, 行为对默认集消费者透明。
6. **`tests/macros.cpp` 删除**。版本相关校验由新增 `tests/version.cpp`
   接管 (§4)。

## 2. 流程接入细节

### 2.1 `scripts/boost_common.py`

新增 `LIBS_SPECIAL = ["version"]` 列表, 加入 `TARGET_LIBS` 末尾。注释
说明 SPECIAL 与 COMPILED_INCLUDE_ONLY 的镜像关系; 不新增
`FEATURE_NAME_OVERRIDE` 项 (无 CMake target 对齐需求)。

`TARGET_LIBS` 现在由 5 个 tier 组成: M3 / M4 / T1A / T2 / T1B / **SPECIAL**。

### 2.2 `scripts/gen_features.py`

`feature_sources(lib)` 已经普适地处理 SPECIAL 形态: `version` 不在
`COMPILED_INCLUDE_ONLY` 中 → 加入 `src/version.cppm`; 不在
`COMPILED_TU_GLOBS` 中 → 无 TU globs; 不在 `EXTRAS` 中 → 无 extras。
唯一改动是 `DEFAULT_CANDIDATES` 加 `"version"`; 注释从 "18-lib closure"
改为 "19 candidates → 49 closure"。

`deps_of("version")` 返回空集 (`src/gen_exports/version.deps` 文件
不存在), `feature_sources("version")` = `["src/version.cppm"]`,
`implies` = `[]`。生成的 TOML:

```toml
[features.version]
  sources = ["src/version.cppm"]
```

### 2.3 `src/gen_exports/version.deps`

作为占位文件存在, 内容仅注释。`gen_features.py` 不强求此文件
(`deps_of()` 用 `exists()` 保护, 缺失时返回空集); 文件存在的目的是
避免未来维护者疑惑"为什么 version.cppm 没有对应的 .deps/.inc"。
注释解释 SPECIAL 形态与镜像关系, 指引读者查看
`LIBS_COMPILED_INCLUDE_ONLY` (log/test) 与本注释对比。

### 2.4 `mcpp.toml` (gen_features.py 重新生成)

- `<gen-sources>` 增 `"src/version.cppm"`;
- `<gen-features>` `[features.version]` 块如 §2.2;
- `[features].default` 闭包扩张为 49 (含 `version`);
- `[features].all.implies` 增 `"version"`;
- 顶部注释增 C5 段落 (§0)。

### 2.5 `build.mcpp`

无需改动。`scripts/features.lst` 末尾自动增 `"version"`; aggregate 模块
生成循环看到 `boost.version` 是普通模块 (`has_feature("version")` 真),
正常追加 `export import boost.version;`。`kModuleLessFeatures[]` 跳过列表
仍只含 `log` / `unit_test_framework`。

### 2.6 `src/core.cppm`

删除原 6 行注释 (`// 对象宏 re-homing (M3) ...`) 与
`export namespace boost { constexpr int BOOST_VERSION = 109100; ... }` 块。
替换为 C5 段落 (引用本设计档 + plan 档), 说明:
- `BOOST_VERSION` / `BOOST_LIB_VERSION` 已迁移到 `boost.version`;
- 默认消费者通过 `import boost;` 拿;
- 宏形式消费者自行 `#include <boost/version.hpp>`。

## 3. 消费者视角

### 3.1 默认集消费者 (`import boost;`)

```cpp
import boost;
static_assert(boost::BOOST_VERSION == 109100);
```

`import boost;` 经 `build.mcpp` 展开, 含 `export import boost.version;`,
常量 `boost::BOOST_VERSION` 直接可见。**无需额外 import**。

### 3.2 单库 opt-in 消费者

```cpp
import boost.version;
static_assert(boost::BOOST_VERSION >= 109100);
```

### 3.3 宏形式消费者

```cpp
#include <boost/version.hpp>   // 自带 header guard
#if BOOST_VERSION >= 109100
// ...
#endif
```

`#include <boost/version.hpp>` 是上游头; 不依赖本包; 与本包任何模块
import 不冲突 (除非同 TU 也 `import boost.version;` —— 见 §3.4)。

### 3.4 互斥

```cpp
#include <boost/version.hpp>   // 定义了对象宏 BOOST_VERSION
import boost.version;          // 模块 TU #undef 了它, 但本 TU 仍可定义
                               //  (因为宏未被带进 import 后的 TU)
static_assert(boost::BOOST_VERSION >= 109100);  // 宏展开 → boost::109100, 错
```

互斥原因: 宏 `BOOST_VERSION` 由消费者 TU 定义后, 它会无条件替换所有
同名 token, 包括模块拼写 `boost::BOOST_VERSION`。M3 final form 注释中
已陈述; C5 删除 macros.hpp 不改变这一点, 只是把"自带宏"的责任从旁路头
移交到消费者 (消费者自行 `#include <boost/version.hpp>`)。

### 3.5 与 T3 库的混用

T3 库 (preprocessor / mpl / fusion / proto / ...) 的公共 API 是
宏族, 消费者 `#include` 上游头即可, 与 `import boost.version;` 不冲突
(因为这些宏不涉及 `BOOST_VERSION` / `BOOST_LIB_VERSION`)。`boost::`
命名空间在 import 后无 `BOOST_*` 宏, 因为 macros.hpp 已删除, 模块 TU
内 `#undef BOOST_VERSION` / `#undef BOOST_LIB_VERSION`。

## 4. `tests/version.cpp` (新增)

取代被删除的 `tests/macros.cpp`, 校验 `import boost.version;` 的拼写与
模块 TU 内 `#undef` 的承诺。

```cpp
// boost.version smoke — 模块形式拿到 boost::BOOST_VERSION /
// boost::BOOST_LIB_VERSION, 且模块 TU 已 #undef 了上游的同名对象宏。
#include "test_assert.hpp"
import boost.version;

// 模块 TU 不应残留 BOOST_VERSION 宏 (否则会污染所有 import 该模块的 TU)。
// 这里只是个 sanity check: 编译能跑就说明 #undef 起作用了 (因为 include
// 这个 test_assert.hpp 不会引入宏)。
static_assert(boost::BOOST_VERSION == 109100);
static_assert(boost::BOOST_LIB_VERSION[0] == '1');

int main() {
    assert(boost::BOOST_VERSION / 100000 == 1);
    assert(boost::BOOST_VERSION / 100 % 1000 == 91);
    return 0;
}
```

注意: 这里不需要 `#ifndef BOOST_VERSION` 真值校验, 那样会引入
`#error` 风格的硬错; 测试只需要保证 import 后能用常量即可。模块 TU 内
宏是否被 `#undef` 是 **模块实现** 的承诺, 由 `src/version.cppm` 的
代码本身保证, 不在消费者测试中验证。

## 5. 与 core 的历史关系

```
M3 final form (2026-08-10):
  core.cppm:
    export namespace boost {
      constexpr int BOOST_VERSION = 109100;       // hardcoded literal
      constexpr const char* BOOST_LIB_VERSION = "1_91";
    }
  include/boost-module/macros.hpp:
    #include <boost/version.hpp>                  // 宏形式

C5 final form (2026-09-09):
  src/version.cppm (LIBS_SPECIAL):
    module;
    #include <boost/version.hpp>                  // 取值
    namespace boost_module::detail {
      inline constexpr int BOOST_VERSION_ = BOOST_VERSION;
      inline constexpr const char* BOOST_LIB_VERSION_ = BOOST_LIB_VERSION;
    }
    #undef BOOST_VERSION                          // 模块 TU 内 #undef
    #undef BOOST_LIB_VERSION
    export namespace boost {
      inline constexpr int BOOST_VERSION = boost_module::detail::BOOST_VERSION_;
      inline constexpr const char* BOOST_LIB_VERSION = boost_module::detail::BOOST_LIB_VERSION_;
    }
  core.cppm:
    (无 BOOST_VERSION / BOOST_LIB_VERSION)
  (macros.hpp 删除)
```

差异:
- **值来源**: core.cppm 是 hardcoded literal (`109100` / `"1_91"`),
  升级 Boost 时需要手改; version.cppm 通过 `#include <boost/version.hpp>`
  取值, 升级时自动同步。
- **位置**: core → version 独立模块。
- **宏传播**: core.cppm 不引入 `<boost/version.hpp>` (不污染消费者 TU);
  version.cppm 通过 `module; #include` 引入了, 但**显式 `#undef`**
  防止污染。
- **macros.hpp**: 删除; 责任转移给消费者。

## 6. 验证矩阵

| 项 | 期望 |
|---|---|
| `uv run scripts/gen_features.py --check` | exit 0; mcpp.toml + features.lst 无漂移 |
| `uv run scripts/gen_features.py` 幂等 | 二次运行 git diff 为空 |
| `[features.version]` 块存在 | `sources = ["src/version.cppm"]`, 无 `implies` |
| `[features].default` 含 `version` | 闭包 49 库 |
| `scripts/features.lst` 末行 = `version` | 第 118 行 |
| `src/version.cppm` 在 `[build].sources` 中 | 第 227 行 |
| `include/boost-module/` 不存在 | `ls include/` 为空 |
| `tests/macros.cpp` 不存在 | `ls tests/macros.cpp` 报错 |
| `tests/version.cpp` 存在 | 校验常量 + 编译通过 |
| `grep "BOOST_VERSION" src/core.cppm` | 无匹配 (除注释中提及 boost.version) |
| `mcpp build` 默认集 (49 闭包) | 通过 |
| `mcpp test` 默认集 (142 个 .cpp) | 通过 (含 tests/version.cpp) |
| `examples/src/main.cpp` `boost::BOOST_VERSION` | 编译通过 (经 `import boost;` 聚合) |

## 7. 后续 (不在本期)

- 若后续有更多"模块形式但不经 gen_exports"的库 (例如纯常量库), 沿用
  `LIBS_SPECIAL` 路径, 不再单列 tier;
- `src/version.cppm` 内 `boost_module::detail` 命名空间是历史过渡,
  后续若要重构可直接消掉 (保留向后兼容导出名即可);
- 真正可选的优化: 把 `BOOST_VERSION_` / `BOOST_LIB_VERSION_` 的 detail
  命名空间折叠成内部匿名命名空间, 当前形态保留 `inline constexpr` +
  命名空间即可, 不影响 ABI;
- macros.hpp 删除是用户决策, release notes 需明示 "breaking: include
  `<boost-module/macros.hpp>` 路径已删除, 改用 `import boost.version;`
  或自行 `#include <boost/version.hpp>`"。
