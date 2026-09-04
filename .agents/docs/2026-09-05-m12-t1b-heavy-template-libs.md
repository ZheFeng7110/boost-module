# M12 — 重型模板库批量接入 (T1b, 12 库模块 + 3 库移交 M13)

> 日期: 2026-09-05 · 里程碑: M12 (`boost-mcpp-all-libs-features-plan.md` §4)
> 前置: M8 (features 基建) · M9 (58 纯头库) · M10 (T3 宏库边界) · M11 (18 编译库)
> 本文记录接入方案与实施结果 (实施后修订)

## 1. 范围与结果

计划 §2 T1b 名单 15 库。**实际接入 12 个模块**:

accumulators / asio / beast / geometry / gil / hana / interprocess /
mqtt5 / multiprecision / numeric / polygon / qvm

全部为 header-only (上游亦无 src TU),feature 面 = 模块接口本身。12 库全部
**import 可用** (smoke 测试 `import boost.<lib>;`,无 include-only 降级)。

**compute / mysql / redis 移交 M13** (用户决策 2026-09-03):核心面硬性要求
外部 SDK 头 — compute 全部实际头 include `CL/cl.h` (OpenCL),mysql/redis 的
聚合头与连接核心 include OpenSSL — 与 T4 外部依赖库同边界,已加入
`boost_common.LIBS_T4` (M13 名单 8→11 库)。

## 2. libs.json curation (12 新库)

- scan 流程同 M9/M11 (仅新库 heuristic + standalone filter,旧库条目保留;
  并行 worker 需 per-PID 临时文件 — 复用 `standalone_<i>.cpp` 名会互踩)。
- 3502 头中保留 1986,剔除 1516:
  - 外部后端: asio/ssl + beast/ssl + beast/websocket ssl (OpenSSL)、
    gil ext io (libjpeg/libpng/libtiff/libraw)、multiprecision
    (gmp/mpfr/mpc/mpfi/tommath/quadmath/eigen 后端)、numeric ublas opencl
    (clBLAS)、polygon gmp_override;
  - impl 头不 standalone (依赖父头声明,门禁/DAG 自动处理);
  - asio 553→234、geometry 1055→687、hana 449→400、numeric 323→191。

## 3. clang 聚合源位置上限 → CI 分组门禁

**问题**: `--features all` (115 feature 全激活) 时 build.mcpp 生成的汇总模块
要在一个 TU 里 import 全部 117 个 CMI (std + 116 boost),clang 报
`ran out of source locations`。clang 源位置空间是 **2^31 硬上限,无 flag 可调**;
header-only 模块的 GMF 文本 include 整棵上游头树 (mqtt5.hpp 全量含 beast+asio),
117 个 PCM 总计 ~2.98GB,远超单 TU 容量。M11 的 103 模块恰好压线。

**方案**: 全量门禁改为按里程碑两层分组 (各自聚合在限内):

- `BOOST_GROUP_A` = default + T1a + T2 (M11 的 103 模块集)
- `BOOST_GROUP_B` = T1b 12 库 (implies 自动拉依赖闭包)

CI (`tests.yml` env) 两组各跑 build+test;本地已双组双平台验证。
**`features = ["all"]` 语义保留** (mcpp.toml 不变),已知限制:全激活聚合超
clang 上限 — 全量消费者应逐库 import;gcc 侧同限未测 (musl 交叉两组同绿)。

## 4. first-wins 归属剧变 (103→115 库重生成)

- **boost.asio 自立**:boost/asio/** 全部实体 (1381 个) 从 process/cobalt 的
  "shared" 收割回 asio 模块;process.inc/cobalt.inc 对应 asio 行消失,
  `.deps` +boost.asio。M11 reapply 的 process.inc asio 锚点守卫全部改
  best-effort。
- **boost.multiprecision 自立**:int128_type/uint128_type/divide 帮手/
  serialization::cpp_int_detail 互操作面从 graph.inc 迁出,graph.deps
  +geometry +numeric (geometry 经 bundled 适配头被 graph 的 GFM 拉入)。
- **boost.numeric 入默认闭包**:date_time (c_local_time_adjustor.hpp →
  numeric/conversion/cast.hpp) 与 log 的 numeric::conversion 实体此前为
  "shared" (date_time 收割),现归属 boost.numeric → date_time.deps
  +numeric → 默认闭包 34→36 (生成器按 .deps 闭包自动计算,计划 §3.2 候选
  18 库不变)。

## 5. 平台守卫 (reapply_hand_edits.py 新增,全部镜像上游条件)

| 模块 | 守卫 |
|---|---|
| hana | ext::boost{,/fusion,/mpl} 与 ext::std 的 using 行根限定 `::boost::` — 块内 `boost`/`std` 段被内层同名命名空间遮蔽 (lookup 从 hana::ext 走出即命中 hana::ext::boost) |
| multiprecision | int128_type/uint128_type/backends::divide_* + serialization::cpp_int_detail 三件 → `BOOST_HAS_INT128`;detail::unmentionable* 无外链 → 删行 |
| qvm | vec_traits_gnuc_impl → `__GNUC__ && __SSE2__` |
| interprocess | managed_windows_shared_memory.hpp GMF include `#if _WIN32||__CYGWIN__`;整个 interprocess::winapi 与 ipwinapiext 块 + 38 个 ipcdetail windows 面 (shm_named_*/spin_*/os_file_traits/winapi_* 等) → `_WIN32` |
| asio | BOOST_ASIO_HAS_FILE 文件面 6 实体;`_WIN32` detail 面 (iocp 全家/winsock/select_reactor 系/windows handle 家族,同 M11 cobalt 清单) |
| beast | file_win32/detail::win32_*/http::detail win32 写算子/unit_test dstream → `_WIN32` |
| process | asio::windows::stream_handle → `_WIN32` (process 自持的收割实体) |

## 6. Vendored 头修改 (重跑 import_boost 需回放,共 5 处 9 文件)

全部同一根因族 — **匿名命名空间实体在"模块 CMI + 消费者 GMF"两路同
mangle 撞名** (gcc `_GLOBAL__N_1` 对同名外层命名空间链是稳定名;M11 §7.4
print_helper 先例),或 TU-local 实体出现在导出面 (gcc "exposes TU-local"):

1. `boost/numeric/ublas/operation/size.hpp`:detail::<unnamed> → 命名
   detail (has_size_type/vector_size_type/matrix_size_type/size_by_*_impl
   出现在导出函数模板返回类型);
2. `boost/asio/{prefer,query,require,require_concept}.hpp`:匿名命名空间
   `static constexpr const impl& X = static_instance<>::instance` →
   `inline constexpr const impl& X`(四个 C++11 时代 workaround 单件);
3. `boost/beast/core/detail/static_const.hpp`:`BOOST_BEAST_INLINE_VARIABLE`
   宏本身 匿名命名空间 → `inline constexpr auto&`(buffer_bytes/close_socket
   等 beast 全部 inline 变量一次修复);
4. `boost/mqtt5/detail/async_traits.hpp`:`constexpr auto X = [](args){}` →
   命名 struct 空函数对象 (闭包类型恒 TU-local;`decltype(X_t)` 用法点改为
   直接用类型名);
5. `boost/parameter/{name,nested_keyword}.hpp`:`BOOST_PARAMETER_NAME_KEYWORD`
   与 `BOOST_PARAMETER_NESTED_KEYWORD_AUX` 的匿名命名空间 keyword 对象 →
   `inline constexpr`(BGL keywords 等;T3 宏库,全局生效 — 外链 inline 化
   严格更利于模块)。

## 7. 已知限制

1. **内部链接对象不可导出** (标准硬限制,M9 hof/units 同型):
   - accumulators 的 `extract::count/mean/...` (const 变量) — 消费者用
     `extract_result<tag::...>` 函数模板 (已导出);
   - mqtt5 的 `prop::session_expiry_interval` 等 constexpr 命名常量 —
     消费者用 `std::integral_constant<property_type, ...>` 拼写;
   - hana 的变量模板 (`int_c`/`integral_c`/`_c` 字面量) — libclang 不暴露
     变量模板 cursor (M9 §6),消费者用 `integral_constant<int, N>` 类模板。
2. **numeric::interval<double> 模块面不可实例化**:默认 `policies<>` 实参
   依赖 `rounded_math<double>` 显式特化,CMI 无法携带 (M9 §6 族) — 消费者
   include `<boost/numeric/interval/interval.hpp>`。
3. **MSVC assert 宏 × 用户定义 operator!**:assert 展开 `(!!(e)) || ...`,
   hana bool 表达式在消费 TU 经 `!` 走 operator! 得错误结果 — 测试/消费者
   侧对模块导出的 bool 常量表达式用显式 `(bool)` 转换 (M9 tribool 陷阱族)。
4. clang 聚合上限见 §3;`--features all` 在 clang 上不可单次构建。
5. compute/mysql/redis 零声明 (§1,M13)。

## 8. 验证矩阵 (2026-09-05 本地)

| 项 | llvm/msvc (Windows) | gcc 16.1 musl 交叉 (POSIX 面) |
|---|---|---|
| 默认 `mcpp build` (36 库闭包) | ✅ | ✅ |
| 默认 `mcpp test` (138 测试) | ✅ 138/138 | (同 M11 基线,链接运行交 CI) |
| A 组 build+test (103 模块) | ✅ 138/138 | ✅ build |
| B 组 build+test (T1b 12 + 闭包) | ✅ 138/138 | ✅ build |
| examples (`import boost;`) | ✅ | — |
| gen_features.py --check | ✅ | — |

smoke 测试 12 个 (tests/{accumulators,asio,beast,geometry,gil,hana,
interprocess,mqtt5,multiprecision,numeric,polygon,qvm}.cpp),覆盖:
accumulator_set+extract_result、io_context+steady_timer+post、http 报文类型、
cartesian 距离/面积/within、rgb8 图像视图、hana tuple/integral_constant/sort、
managed_heap_memory、connect_props+qos_e、cpp_int 大数算术/gcd、
numeric_cast+ublas+odeint、point/interval/rectangle、vec/quat/rotz_mat。
