# M9 — 纯头库批量接入 (T1a, 58 库)

> 日期: 2026-08-17 · 里程碑: M9 (`boost-mcpp-all-libs-features-plan.md` §4)
> 前置: M8 (features 基建, 27 库) · 本文记录实现与验证过程

## 1. 范围与分类结果

计划 §2 的 T1a "~63 库" 以生成器结果为准收敛为 **58 库** (含/除 变动):

- **接入 58 库**: align array assert assign bimap bloom callable_traits
  circular_buffer compat concept_check config convert crc decimal describe dll
  dynamic_bitset flyweight format function functional hash2 heap histogram icl
  integer intrusive leaf lexical_cast lockfree logic move multi_array
  multi_index openmethod outcome parser pfr poly_collection pool property_map
  property_tree ptr_container ratio safe_numerics signals2 smart_ptr sort
  statechart stl_interfaces throw_exception tokenizer type_index unordered
  utility uuid winapi yap
- **排除与降级** (记录于 §5):
  - `conversion`: 1.91 无任何头 (stub, 仅 meta/test) → 非库
  - `static_assert`: 纯宏 0 实体, 且模块名非法 (`static_assert` 是关键字,
    clang 拒绝 `export module boost.static_assert;`) → include-only (T3 类)
  - `hof` / `units`: 公共 API 是 internal-linkage `static constexpr` 对象
    (boost::hof::compose/_1、boost::units::si::meter 等), using-declaration
    无法导出 → include-only
  - `predef`: 纯 .h 宏库 (无 .hpp) → T3 include-only (前序已定)
  - `coroutine2` / `property_map_parallel`: 依赖 context (T4) / 无汇总根头
    → 移交 M13 / 非库

## 2. 生成器管线增强

### 2.1 libs.json 全量重生成 + curation

- `--scan` 全 85 库重生成 (2338 头); 既有 27 库保留 M2-era 人工 curation
  (新 scan 会误删自足性不足但有效的头, 如 chrono io facets、regex
  sub_match.hpp — 合并策略: 旧 27 库条目原样保留, 新库用 scan 结果)
- 新 curation:
  - `config`: 只保留 `boost/config.hpp` — 全量 39 头会把互斥的
    platform/*.hpp 变体全收进 GFM, MSVC 风味缺 unistd.h 编译失败
  - `multi_index`: 补 `multi_index_container.hpp` (+fwd) — 扫描漏掉,
    消费者实例化 undefined template
  - `utility`: 补 `boost/compressed_pair.hpp` (utility 的公共 API)

### 2.2 dep_graph 传递遍历 (拓扑序修复)

原 dep_graph 只扫一层的直接 include, **`boost/<lib>.hpp` 单头聚合 include 不可见**
(`_lib_of_include` 拒绝带点名字), 且经非目标库中间层的传递边丢失:
icl → date_time(非目标) → tokenizer.hpp 导致 icl 先于 tokenizer 处理,
first-wins 把 tokenizer 的实体 (token_iterator 等) 全抢走, tokenizer 模块只剩
1 个导出。修复: dep_graph 沿**非目标库头文件传递遍历** (目标库根/系统头停止),
单头聚合 include 也识别 (`boost/<lib>.hpp`)。

### 2.3 using-injection linkage 校验 (M9 引入的回归源)

collect_injections 原来不检查目标实体 linkage: hof 的 `using
placeholders::_1;` (internal linkage static constexpr) 注入成功但模块
无法导出 → 编译失败。修复: 注入名解析到目标声明后检查外部链接
(全部同名 cursor 必须 external); curated 同样校验 (collect_curated 加
usr_index 参数)。

### 2.4 using-declaration 目标形态扩展

`_using_target_name` 现在返回 (注入名, 目标名) 二元组, 支持:

| 形态 | 例子 | 注入名 | 导出行 |
|---|---|---|---|
| 相对 | `using range::count;` (namespace boost 内) | boost::count | `using boost::count;` |
| 全限 | `using boost::system::error_code;` | 同左 | 同左 |
| 全局 `::` | `using ::boost::bimaps::bimap;` | boost::bimap | `using boost::bimap;` |
| 全局非 boost | `using ::GetCurrentProcessId;` (winapi 内) | boost::winapi::GetCurrentProcessId | `using ::GetCurrentProcessId;` |
| std 别名 | `using std::ratio;` (Boost.Ratio 1.91 是 std::ratio facade) | boost::ratio | `using std::ratio;` |

后两种不能 `using boost::X;` (using-of-using 不可导出 / 未限定名解析失败),
直接导出目标本身。std:: 与全局目标跳过 boost qname 校验 (恒外部链接)。

### 2.5 归属按定义处而非首声明

`class rational` 在 boost/integer/common_factor_rt.hpp (integer 库) 有前向声明,
`build_usr_index` 首声明 wins 使 integer 抢走 USR → rational 模块丢失本体。
collect_candidates 改为: 非定义声明解析到定义处 (`get_definition()`) 再判
归属。

## 3. 平台守卫 (mingw 快照 × 其他风味)

MSVC 风味批量验证 (用各模块真实 GFM + .inc 在
`--target=x86_64-pc-windows-msvc` 下编译) 找出 26 处缺失实体, 全部加 .inc
`#if` 守卫 (reapply_hand_edits.py, 条件镜像上游头):

- config: int128_type/uint128_type → `BOOST_HAS_INT128` (M3 守卫从 core.inc
  移来 — suffix.hpp 实体随 config 模块化归属变化)
- decimal: builtin_int128_t/uint128_t/128_pow10 → `BOOST_DECIMAL_HAS_INT128`;
  ieee754_binary80 → `LDBL_MANT_DIG == 64 && LDBL_MAX_EXP == 16384`
- dll: itanium demangling parser 12 实体 + demangle_symbol →
  `!defined(_MSC_VER)`
- functional/poly_collection: mpl gcc-preprocessed vector/map aux 实体 →
  `defined(__GNUC__)` (M3 variant.inc 同款)
- intrusive: builtin_clz_dispatch → `defined(__GNUC__)`
- thread: make_signed/make_unsigned → `BOOST_HAS_INT128`
- range: `using std::random_shuffle;` → `defined(__GLIBCXX__)` (C++17 移除,
  仅 libstdc++ 保留)
- hof: 原守卫随 include-only 移除

另: `-Wno-invalid-specialization` 加入全局 cxxflags — poly_collection 的
detail 头特化 std::is_void (is_final/is_invocable fallback hook), clang+MSVC
STL 连纯 include 消费者都会硬报错, 该标志只降级此诊断。

## 4. 测试

60 个新 smoke 测试 (每库 1 文件, import + 2~3 代表性实体)。发现并记录的
**测试写法陷阱**:

- `assert(tribool_expr)` 在 MSVC 上恒失败 — MSVC assert 宏
  `(!!(x)) || (_wassert(...), 0)`, 用户定义 operator|| 不短路, 右侧
  `_wassert` 无条件执行并 abort。需先 `bool(...)` 转换
- `import std` + include 拉 `<type_traits>` 的头在同一 TU → std 变量模板
  重定义 (MSVC 风味) — 宏测试 (describe/statechart/openmethod/hof/units)
  改纯头包含
- `lexical_cast<bool>` 在 clang+MSVC STL 下连纯 include 也崩溃 → 上游问题,
  测试不覆盖
- dll program_location 在 MSVC 风味崩溃 (path 转换) → 测试只验默认构造
- 模块不能导出 std::tuple_size 特化 (描述在 GMF 中声明, 消费者不可见) —
  describe 测试不用 tuple_size_v

## 5. 验证矩阵 (本地 llvm/msvc)

| 项 | 结果 |
|---|---|
| `mcpp build` (默认 31 库闭包) | ✅ |
| `mcpp build --features all` (85 模块 + 编译 TU) | ✅ |
| `mcpp test` (88 测试, 含 60 新) | ✅ 88/88 |
| examples (`import boost;`) | ✅ |
| gen_features.py --check | ✅ |

## 6. 已知限制与后续

- **变量模板不收集**: libclang 不暴露 variable template cursor
  (pfr::tuple_size_v 等缺失), 已用类模板替代; M12 如需可走 curated
- **hof/units 降级 include-only**: internal-linkage API 对象无法导出, 标准
  层面的硬限制; 消费者 include + import 混用 (标准允许)
- **multi_array 的 boost::extents**: 匿名命名空间对象, 不可导出; 消费者用
  容器式构造 (`boost::array` dims)
- **T1b/T2/T3/T4** 移交 M10–M13
- POSIX 腿 (linux/mac CI) 的守卫正确性由 CI 验证 — 本轮 .inc 守卫均镜像
  上游头条件, 与本机 mingw 快照同源
