# boost-module 使用文档

## 1. 依赖声明

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

> **clang 下不要用 `features = ["all"]`**: 全部 CMI 约 2.98GB，超过 clang
> 2^31 源位置上限，报 "ran out of source locations"，无 flag 可调。
> **全量需求请逐库 import**；gcc 侧同限未实测。

## 2. 三种消费形态

### 2.1 模块 import（116 库）

```cpp
import boost.filesystem;   // 单库
import boost;              // 汇总: 恰好 re-export 当前激活的库 (零激活时是合法空壳)
```

API 拼写与上游一致；自由运算符已显式导出，friend 运算符经 ADL。

### 2.2 纯 include-only（20 库）

无 feature 无模块，直接 `#include` 上游头，可与模块 import 同 TU 混用
（标准允许）。宏 API（BOOST_PP_/BOOST_FOREACH/BOOST_DESCRIBE_*/
BOOST_OPENMETHOD*/BOOST_SCOPE_EXIT_* 等）永远只能来自 include ——
宏是预处理器层面的 API，不跨模块边界。

```cpp
#include <boost/preprocessor/cat.hpp>   // 宏 API: 只能 include
#include <boost/foreach.hpp>
import boost.core;                      // 模块化库照常 import, 两者共存

static_assert(BOOST_PP_CAT(1, 2) == 12);
BOOST_FOREACH (int x, vec) { /* ... */ }
```

名单: preprocessor / mpl / fusion / proto / spirit / xpressive / typeof /
vmd / phoenix / parameter / metaparse / function_types / tti /
local_function / msm / foreach（宏驱动 16）+ exception、describe、
openmethod、scope_exit（降级 4）。

### 2.3 编译库 include-only（2 库: log、test）

feature 保留库 TU 编译链接，但没有模块接口。

**log**: `--features log` + `#include <boost/log/...>` + 链接库 TU。

**test**（`unit_test_framework` feature）: **双形态消费，两形态不可同链接**
（框架 TU 与 included 聚合实现符号冲突，二选一）:

| 形态 | feature | include | 链接 |
|---|---|---|---|
| 编译框架（官方推荐） | `--features unit_test_framework` | `<boost/test/unit_test.hpp>`（+ `BOOST_TEST_NO_MAIN` + `<boost/test/impl/unit_test_main.ipp>` 取 runner，或自持 main） | 包内框架 TU |
| 纯头文件库（官方可选） | 不启用 | `<boost/test/included/unit_test.hpp>`（聚合头，自带 main） | 无 |

```cpp
// 编译形态 (features = ["unit_test_framework"]):
#define BOOST_TEST_MODULE my_suite
#define BOOST_TEST_NO_MAIN
#include <boost/test/unit_test.hpp>
#include <boost/test/impl/unit_test_main.ipp>

BOOST_AUTO_TEST_CASE(t) { BOOST_TEST(1 + 1 == 2); }

int main(int argc, char* argv[]) {
    return boost::unit_test::unit_test_main(&init_unit_test_suite, argc, argv);
}
```

```cpp
// 纯头形态 (不启用 feature):
#define BOOST_TEST_MODULE my_suite
#include <boost/test/included/unit_test.hpp>   // 自带 main
BOOST_AUTO_TEST_CASE(t) { BOOST_TEST(1 + 1 == 2); }
```

## 3. feature 选择语义

- 每个库对应一个 feature（`scripts/gen_features.py` 生成，勿手改），
  共 118 个 = 116 模块 feature + log + unit_test_framework。
- **默认集 = 49 库闭包**，覆盖核心面（19 个原核心库 + config/assert/
  utility/move 等基建库 + `boost.version`）；其余 opt-in。
- feature 可声明 `implies`（传递闭包），例如 `--features log` 拉齐链接依赖。

## 4. 版本常量（`boost.version`）

```cpp
import boost.version;    // 默认集内, import boost; 已自动 re-export
static_assert(boost::BOOST_VERSION == 109100);
static_assert(boost::BOOST_LIB_VERSION[0] == '1');
```

- 取值来自上游 `<boost/version.hpp>`，以 `inline constexpr` 在 `boost::`
  命名空间导出（拼写保持）。
- 宏形式（`#if BOOST_VERSION >= 109100`）由消费者自行
  `#include <boost/version.hpp>`；**同一 TU 内宏定义与模块拼写互斥**
  （宏会展开 `boost::BOOST_VERSION` → `boost::109100`），二选一。

## 5. 消费者注意事项

- **必须自带 std 表面**（`import std;` 或 include）—— boost 实体签名引用
  std 类型的运算符在纯 import TU 不可见（设计使然）。
- gcc 16.1 存在模块缺陷家族，消费方式三分规则: ① 正常 import；
  ② import + 补标准头（`<new>`/`<typeinfo>`）；③ 纯 include。
  逐库核实见 [architecture.md §4](architecture.md#4-已知限制-消费者须知)。
- 特性宏一律构建期固定，消费者无法自定义任何 BOOST_* 特性宏；
  filesystem 固定 v3 API、thread 固定 v2 API（`unique_future`）、
  stacktrace basic 等裁剪清单见 [architecture.md §4.1](architecture.md#41-工具链标准硬限制)。
- M13 外部依赖库（context / fiber / coroutine / locale / mpi / python /
  parameter_python / graph_parallel / compute / mysql / redis）预览版
  **不支持**。
- 平台支持范围见 [architecture.md §5](architecture.md#5-支持矩阵)
  （mingw 与真 MSVC 不承诺）。
