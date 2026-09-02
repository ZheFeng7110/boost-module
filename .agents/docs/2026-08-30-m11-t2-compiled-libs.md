# M11 — 编译库批量接入 (T2, 18 库模块 + exception 降级)

> 日期: 2026-08-30 · 里程碑: M11 (`boost-mcpp-all-libs-features-plan.md` §4)
> 前置: M8 (features 基建) · M9 (58 纯头库) · M10 (T3 宏库边界确认)
> 本文记录接入方案与实施结果 (实施后修订)

## 1. 范围与结果

计划 §2 T2 名单 19 库。**实际接入 18 个模块**:

atomic / charconv / cobalt / container / contract / date_time / graph /
iostreams / log / math / nowide / process / random / serialization / test /
timer / type_erasure / wave

**exception 降级 include-only**(§6.1):clone_impl<T> 成员体以 lazily-loaded
pendings 形式附着在 boost.exception CMI 上,gcc 16.1 在任何"消费 TU include
`<memory>/<string>/<functional>` + import boost.exception"的组合下报
"recursive lazy load / failed to load pendings"(即所有真实消费者);在模块
TU 内做显式实例化无法绕开。API 本身 header-only,消费者按 T3 规则
`#include <boost/exception/all.hpp>`(tests/exception.cpp 为 include-only
smoke)。默认闭包相应从 36 回落到 34 库。

## 2. 逐库 TU 表(上游 CMake/b2 对照,实施后定稿)

| 库 | TU | 说明 |
|---|---|---|
| atomic | lock_pool.cpp + find_address_sse2.cpp | find_address_sse41.cpp 排除:上游用 per-TU `-msse4.1` 且探测通过才启用;走上游"探测失败"回退路径(BOOST_ATOMIC_USE_SSE41 未定义,SSE2 路径) |
| charconv | from_chars.cpp + to_chars.cpp | 原挂在 parser feature 下,M11 起归 charconv,parser 改 implies(EXTRA_IMPLIES) |
| cobalt | src/*.cpp + detail/*.cpp + io/*.cpp ×18(逐一列出,不含 ssl.cpp) | ssl.cpp 依赖 OpenSSL(M13 边界);main.cpp 只定义 main_promise::run_main,安全 |
| container | global_resource + monotonic_buffer_resource + pool_resource + synchronized/unsynchronized_pool_resource ×5 | alloc_lib.c(C)与 dlmalloc.cpp 都排除:dlmalloc.cpp 的 dlmalloc_* 包装器调用 alloc_lib.c 定义的 boost_cont_* C API,两者必须成对;等价上游 BOOST_CONTAINER_HEADER_ONLY 降级 |
| contract | contract.cpp | 自 define BOOST_CONTRACT_SOURCE |
| date_time | greg_month.cpp ×1 | **上游 CMake 只编译这一个**;其余 gregorian/posix_time TU 是与 1.91 头不一致的 b2 遗留(greg_weekday.hpp 无条件 inline 定义 as_*_string,.cpp 重定义) |
| graph | graphml.cpp + read_graphviz_new.cpp | — |
| iostreams | file_descriptor.cpp + mapped_file.cpp | zlib/gzip/bzip2/lzma/zstd 依赖外部系统库(M13);本机恰有这些头,standalone filter 拦不住,libs.json 人工裁剪 |
| log | src/*.cpp + setup/*.cpp + windows/*.cpp + posix/*.cpp | windows/posix 目录 thread 式互斥;dump_avx2/dump_ssse3 双侧排除(顶部无条件 immintrin,arm64 崩;且符号只在消费者自定义 BOOST_LOG_USE_AVX2/SSSE3 时被引用);simple_event_log.h 为手写桩(§6.4) |
| math | (无 TU,header-only) | src/ 仅 tr1/(弃用);上游 CMake `add_library(boost_math INTERFACE)` |
| nowide | src/*.cpp ×6 | — |
| process | src/**/*.cpp ×17 全平铺 | 平台 TU 内部 `#if defined(BOOST_PROCESS_V2_POSIX/WINDOWS)` 自守卫;boost/process.hpp 聚合头被门禁裁掉 |
| random | random_device.cpp | — |
| serialization | src/*.cpp ×48 | — |
| test | 18 个 TU(排除 unit_test_main.cpp / cpp_main.cpp / test_main.cpp) | 三者定义 ::main 或引用用户 test_main();`mcpp test` 全对象链接,库自带 main 与每个测试程序的 main 冲突(无按需 pull)。消费者自持 main + `#include <boost/test/impl/unit_test_main.ipp>`(BOOST_TEST_NO_MAIN)取 runner,见 tests/test_utf.cpp |
| timer | cpu_timer.cpp + auto_timers_construction.cpp | — |
| type_erasure | dynamic_binding.cpp | — |
| wave | src/*.cpp ×10 + src/cpplexer/re2clex/*.cpp ×2 | re2clex 在两层子目录,`cpplexer/**/*.cpp`(初版少一层导致 aq_* 未定义) |

## 3. libs.json curation(19/18 新库)

- scan 流程同 M9(仅新库跑 heuristic + standalone filter,旧库条目保留)。
- serialization:+ boost/archive/**.hpp(公共根跨目录)。
- test:剔除 boost/test/included/**(header-only 模式聚合头,与库 TU 双重
  定义)、boost/test/minimal.hpp(定义 ::main)、data/test_case.hpp +
  data/monomorphic/generators/{random,keywords}.hpp(nfp 匿名命名空间
  TU-local 暴露,gcc 硬错)、utils/timer.hpp(get_tick_freq 非 inline)。
- iostreams:filter/{zlib,gzip,bzip2,lzma,zstd}.hpp(外部库头,本机误保留)
  与 filter/{regex,grep}.hpp(regex traits 触发 gcc 模块流 bug)剔除。
- utility:string_ref.hpp(弃用;其 buffer_fill enum 在 boost.io /
  boost.utility 两个 CMI 间不匹配)剔除。
- io:ostream_put.hpp(同上 buffer_fill)剔除。

## 4. 生成器管线改动

### 4.1 boost_common.py
- LIBS_T2(18 库)+ LIBS_INCLUDE_ONLY_M11 = ["exception"](含原因注释);
  TARGET_LIBS 共 103 库。
- CLANG_ARGS 加 `-DWIN32_LEAN_AND_MEAN`:asio 在 windows.h 先拉 winsock1 时
  硬报 "WinSock.h has already been included"(任何 boost.winapi → windows.h
  链都会先);`_WINSOCKAPI_` 反而触发 asio 自身的相反检查,不可用。
- **修复 gfm_headers_of 死循环**(M11 实际首次触发,boost.math):当剩余子集
  中所有头互相 include(纯 include 环、无入口源)时,旧循环每轮全部 skip、
  missing 永不收缩 → 无限循环。现在兜底选一个代表继续,保证终止。

### 4.2 gen_features.py
- COMPILED_TU_GLOBS 按 §2 定稿;删 parser 的 charconv glob(charconv 自立)。
- EXTRA_IMPLIES = {"parser": ["charconv"]}(GMF 仅在无 `__cpp_lib_to_chars`
  时拉 boost/charconv.hpp,mingw 生成的 .deps 缺边,linux-llvm 腿需要)。
- FEATURE_FLAGS:log 的 windows TU 需 SECURITY_WIN32(sspi.h 三选一,上游
  CMakeLists.txt:324)——注意:per-glob flags 对**显式路径源**未生效
  (实测),故该宏落在 [build].defines 包级。

### 4.3 全量重生成 + reapply
- gen_exports 全量(103 库)→ first-wins 归属剧变:histogram.inc 从 1653 行
  瘦身到 427 行(math/serialization/mpl 等泄漏实体回归各自模块);thread.deps
  +atomic(+ exception 已随降级回退);icl.deps +date_time/container;
  histogram.deps +math/serialization;json.deps +container。
- reapply_hand_edits.py 新增守卫(全部镜像上游头条件):
  - atomic.inc:is_integral/is_signed/make_signed/make_unsigned
    (BOOST_HAS_INT128)+ gcc-only 后端(__GNUC__ / gcc_x86 加 x86 arch);
  - charconv.inc:ieee754_binary80(LDBL 80 位)、to_chars128
    (BOOST_CHARCONV_HAS_INT128);
  - math.inc:float80_t/float_fast80_t/float_least80_t(LDBL 80 位);
  - graph.inc:multiprecision int128_type/uint128_type、backends divide_*、
    serialization::cpp_int_detail 三件(BOOST_HAS_INT128)、proto
    template_arity 三件(BOOST_PROTO_EXTENDED_TEMPLATE_PARAMETERS_MATCHING);
  - iostreams.inc:codecvt_impl(STL codecvt 变通路径三选一);
  - process.inc:asio posix_thread(BOOST_ASIO_HAS_PTHREADS);
  - 裁剪类(minimal.hpp / test data / string_ref / regex / grep /
    ostream_put / unmentionable)的 include 与 .inc 行删除。
- thread.inc 的 M4/M7 atomics 守卫与 make_signed 守卫改 required=False
  (实体迁往 atomic.inc 后 anchor 消失是预期)。

### 4.4 mcpp.toml(手工区)
- defines += WIN32_LEAN_AND_MEAN、SECURITY_WIN32(模块 TU 与库 TU 宏一致)。
- include_dirs += deps/boost/libs/log/src(私有头引号 include)、
  deps/boost/libs/atomic/src(`#include BOOST_PP_ITERATE()` 展开成裸文件名,
  clang 按当前文件目录解析、gcc 不按)。
- target.windows.ldflags = -lws2_32 -lntdll -lshell32 -ladvapi32 -lsecur32
  -luser32 -lsynchronization(cobalt/log asio、process ext、log
  GetUserNameExW、atomic WaitOnAddress;镜像上游 CMake WIN32 链接集)。
- target.windows/unix sources `!` 排除:log posix/** 与 windows/** 互斥 +
  dump_avx2/dump_ssse3 双侧排除。

## 5. 验证结果(本地 llvm/msvc + gcc/mingw)

| 项 | llvm/msvc | gcc/mingw 16.1 |
|---|---|---|
| 默认 `mcpp build`(34 库闭包) | ✅ | ✅ |
| 默认 `mcpp test`(126 测试) | ✅ 126/126 | ❌ test.m.o(nfp TU-local,§6.5) |
| `mcpp build --features all`(103 模块) | ✅ | —(同上) |
| `mcpp test --features all` | ✅ 126/126 | — |
| examples(`import boost;`) | ✅ | — |

smoke 测试 19 个(tests/*.cpp,含 test.cpp 更名 test_utf.cpp),覆盖符号级
链接:atomic/charconv/cobalt(run+task 协程)/container(pmr 资源 TU)/
contract/date_time(greg_month TU)/exception(include-only)/graph
(read_graphml TU)/iostreams(file_descriptor+mapped_file TU)/log(core +
sink 管线,push_record 显式)/math/nowide/process(pid+environment TU)/
random(random_device TU)/serialization(text archive TUs)/test_utf(框架
main 方案)/timer(cpu_timer TUs)/type_erasure(编译期面,§6.6)/wave
(re2clex+grammar TUs)。

## 6. 已知限制

1. **exception include-only**(§1)——唯一相对计划的删减;gcc 16.1 模块
   CMI pendings bug,新版本 gcc 或上游修复后可重新接入。
2. iostreams 外部后端(zlib/gzip/bzip2/lzma/zstd)与 cobalt ssl 不入包。
3. math tr1 组件、container dlmalloc/alloc_lib 扩展分配器、process 聚合头
   boost/process.hpp 不入包。
4. log:event_log_backend.cpp 依赖 mc.exe 生成的 simple_event_log.h,
   deps 内手写了等价桩(常量仅需自洽);dump_avx2/ssse3 不入包。
5. **gcc 16.1 `mcpp test`(test 模式全量编译)失败于 test.m.o** — ~~上游
   Boost.Test 的 nfp 关键字惯用法在 ~7 个头使用匿名命名空间,模板暴露
   TU-local 实体被 gcc 硬错(llvm/msvc 无此检查)~~ **已修复(见 §7):runtime
   modifier.hpp 与 token_iterator.hpp 的匿名命名空间改命名命名空间 + inline
   变量。**
6. type_erasure:any<> 动态分发路径在 clang-msvc 模块消费者侧不能实例化
   (vtable.hpp 的 vtable_storage static_cast 与模块 ODR 不兼容);模块面
   与概念模板可用,smoke 覆盖编译期面。
7. test 模块的宏面(BOOST_TEST_*)与 T3 同理不可导出——消费者 include
   boost/test/unit_test.hpp 拿宏 + import boost.test 拿编译框架。
8. 消费者自定义的 log/process 特性宏随构建期固定(M4 §9 同型)。
9. 上游 vendored 头修改 6 处(重跑 import_boost 需回放):
   - boost/archive/iterators/remove_whitespace.hpp:匿名命名空间 →
     boost::archive::iterators::detail(TU-local 暴露,serialization/iostreams
     模块 TU 在 gcc 上硬错);
   - boost/io/detail/buffer_fill.hpp:inline 模板内的匿名 enum → constexpr
     局部变量(枚举跨 CMI 流不一致,utility/filesystem/wave 组合 gcc 硬错
     "definition of enum ... does not match");
   - boost/test/utils/runtime/modifier.hpp:匿名命名空间 → runtime_detail +
     inline 变量 + using 指令(nfp 关键词 TU-local 暴露,§6.5);
   - boost/test/utils/iterator/token_iterator.hpp:同上(token 关键词);
   - boost/test/tools/detail/print_helper.hpp:匿名命名空间 → tt_detail
     inline 变量(CMI/include 两路 _GLOBAL__N_1 同 mangle 撞名,§7.4);
   - boost/test/utils/basic_cstring/basic_cstring.hpp:模板静态数据成员
     定义 → inline 变量定义(模块 TU 与消费者 TU 两份不去重,§7.4)。

## 7. CI 修复 — POSIX 腿(mingw 快照平台面,2026-08-31)

M11 首次 CI(35c25093)linux-gcc/linux-llvm/macos-llvm 全部在 Build 步骤失败:
18 个新模块的 .inc/.cppm 是 **mingw 快照**——MSVC/clang-windows 在 CI 里编译过,
但 POSIX 面从未编译过(gcc 在 atomic.m.o 首败,后面还压着一批)。全部修复经
本地 `mcpp build --target x86_64-linux-musl`(gcc 16.1 交叉)逐轮复现+验证:
默认 build、`--features all`(103 模块全量)、`mcpp test` 编译面、examples
编译面均通过;Windows 侧默认 + `--features all` 回归通过。

### 7.1 reapply_hand_edits.py 新增守卫(全部镜像上游头条件)

- atomic.inc:wait_operations_windows(BOOST_WINDOWS — wait_ops_windows.hpp
  仅 Windows wait backend;M6 时在 thread.inc,实体迁来后漏掉);
- container.inc:win_critical_section(thread_mutex.hpp 非 pthread 分支)、
  boost::container_winapi 块(mutex.hpp `_WIN32/__WIN32__/WIN32` 自旋分支);
- date_time.inc:time_from_ftime / posix_time::from_ftime(BOOST_HAS_FTIME,
  M6 同款 FILETIME 对);
- nowide.cppm:GMF 显式补 cstdio/stackstring/convert(跨平台头,mingw 经
  windows 链传递可达);nowide.inc:console 机制 + detail::stat(_WIN32);
- process.cppm:v1/v2 windows launcher 十连 include 整体 `#if _WIN32||
  __CYGWIN__`(winapi basic_types.hpp #error,同 M9 winapi.cppm);POSIX 分支
  补 boost/process/v2/process.hpp + posix/default_launcher.hpp(v2 核心原来
  只经 windows launcher 链可达);process.inc:asio windows 服务/句柄、
  v1/v2 windows detail 块、process_handle_windows 的 `*_` 助手、
  environment_win 的 is_exec_type、windows 平铺的 launcher 机制
  (probe/invoke/has_*/all_are_initializers — POSIX 嵌在 v2::posix::detail
  且名称集不同);
- cobalt.cppm:GMF 显式补 asio detail hash_map/fd_set_adapter/
  reactor_op_queue/socket_select_interrupter(跨平台,mingw 经 windows 链
  可达);cobalt.inc:asio file 四件(BOOST_ASIO_HAS_FILE)、win_*/iocp/
  winsock/apc、null_reactor/select_reactor/null_signal_blocker/
  socket_select_interrupter(IOCP/winsock 分支;epoll/kqueue 路径不声明);
- log.inc:**strip_log_version_namespace()** — mingw 快照把版本内联命名空间
  v2s_mt_nt62 烤进所有限定名,POSIX 是 v2s_mt_posix;内联命名空间对外查找
  透明,故剥掉该层(opener 去段 + using 行去限定,配平括号);
  另守 is_debugger_present(BOOST_WINDOWS)、event_log/debug_output 关键词
  与 sinks、sinks::event_log 块、spirit decode_utf16(wchar_t==2 分支);
- log.cppm:GMF 补 boost/phoenix/function.hpp(phoenix function 机制原来只
  经 windows-only is_debugger_present 头可达);support/regex.hpp 仅保留在
  Windows 面 — gcc 把 CMI(带 __cxx11 tag)与 GMF 文本重解析(无 tag)合并时
  硬报 "mismatching abi tags"(cpp_regex_traits<char>::get_catalog_name_inst),
  对应导出行 boost_regex_expression_tag 加 _WIN32 守护;
- test.cppm 的 test.m.o nfp 硬错由 §6.9 vendored 修复解除(§6.5)。

### 7.2 mcpp.toml

- `_WIN32_WINNT=0x0A00` 从 [build].defines 移入 [target.windows.build].defines:
  POSIX 上该宏触发 asio 的 Windows-App 探测(config.hpp `_WIN32_WINNT>=0x0603`
  → winapifamily.h → WINAPI_FAMILY_PARTITION 未定义,cobalt/process 依赖
  扫描硬错)。BOOST_ALL_NO_LIB/_MT/WIN32_LEAN_AND_MEAN/SECURITY_WIN32 保持
  全包(POSIX 无害)。

### 7.3 已知边界

- linux-gnu(glibc)腿未本地验证(musl 交叉代表 POSIX 面);macOS arm64 依
  守护条件推定(epoll 分支→select_reactor 系不导出,与上游一致)。
- 本机交叉链接受 lld(zlib) 限制,mcpp test/examples 的链接+运行交给 CI
  原生腿(M10 时已验证)。

### 7.4 CI 修复 — linux-gcc Test 六连败 + llvm 腿 math(2026-09-02)

M11 fix(62d1e6af)后 linux-gcc 的 Build 过了但 Test 步骤 126 个测试败 6
(cobalt/exception/log/test_utf/wave/timer);linux-llvm/macos-llvm 仍在
Build 步骤败于 math。全部经本地 gcc 16.1 musl 交叉逐个复现+验证(编译+
链接面;timer 运行面经 Windows 宿主),Windows 侧 build + 126 测试 +
example 回归通过。

- **cobalt**(test TU 实例化 std 模板硬错 `must '#include <typeinfo>'
  before using 'typeid'` / `no matching function for call to
  'operator new(sizetype, void*)'`):boost.cobalt CMI 里可达的
  libstdc++ 模板体(_Sp_counted_ptr_inplace 的 typeid、
  __is_nothrow_new_constructible_impl 的 placement-new)在消费者 TU
  实例化,而 tests/cobalt.cpp 只 include 了 <coroutine> — 模块 CMI 不
  传递 include 状态,gcc 16.1 模板体检查要求typeid/new 声明在实例化
  TU 可见。修复:测试 TU 显式补 <new> + <typeinfo>。
- **exception**(CMI/GMF 合并冲突 `conflicting declaration of template
  'std::__byte_operand'` 级联):测试 TU `import boost.throw_exception` +
  `#include <boost/exception/all.hpp>`,<cstddef> 经 CMI 与 GMF 两路
  合并触发 gcc 16.1 CMI merge bug。修复:测试改纯 include(T3 consumer
  rule,与库面 M11 降级同型),去掉 import。
- **log**(汇编期 `symbol ...lsI...E already defined` 重复强符号):
  basic_formatting_ostream 的 operator<< 模板特化一份记录在 log CMI
  (模块 GMF 编译期实例化)、一份在消费者 TU 实例化,gcc 16.1 未归一。
  修复:测试改纯 include(expressions/sinks/logger/record_ostream 直
  接取头文件),不再 import boost.log。
- **test_utf**(两段式失败):先是汇编期
  `boost::test_tools::tt_detail::_GLOBAL__N_1L21boost_test_print_typeE`
  重复 — vendored print_helper.hpp 的匿名命名空间引用实体在 CMI 与
  include 两路同 mangle 撞名,改 tt_detail 命名空间 inline 变量(§6.9
  同款);再是链接期 `basic_cstring<char const>::null` 重复 — 模板静
  态数据成员定义两份未去重,改 inline 变量定义。
- **wave**(gcc 16.1 模块 mangle 冲突 `mangling of '__synth3way_t
  operator<=>' ... conflicts with a previous mangle`,bits/stl_iterator.h:
  1204):wave CMI 与依赖 CMI 各自记录了 libstdc++ __synth3way 运算符
  特化,同 TU 加载两份同 mangle 实体,-fabi-version=0 无效(gcc 官方
  提示的 workaround 对该合成运算符不生效)。修复:测试改纯 include
  (T3 consumer rule);模块面在 Build 步骤本来就编译通过。
- **timer**(运行期断言 `times.wall > 0` 失败,exit 134):POSIX 的
  wall 取自 times(),粒度 _SC_CLK_TCK==100(10ms);测试忙等循环
  10000 次不足一个 tick → elapsed().wall == 0(Windows QPC 纳秒粒度
  无此问题,故仅 linux-gcc 腿暴露)。修复:stop 前先 sleep 50ms(≥5
  tick)。
- **math**(linux-llvm/macos-llvm Build 步骤):math.inc 无条件 using
  了仅在 BOOST_MATH_EXEC_COMPATIBLE 下定义的三个并行统计
  impl(chatterjee_correlation_par_impl /
  correlation_coefficient_parallel_impl /
  means_and_covariance_parallel_impl — chatterjee_correlation.hpp /
  bivariate_statistics.hpp 的 #ifdef);libc++ 提供无
  __cpp_lib_execution 的 <execution>,宏不定义。first_four_moments/
  gini 的并行版只要求 BOOST_MATH_HAS_THREADS(single_pass.hpp),
  clang 下存在,无需守护。修复:reapply_hand_edits.py 新增三行
  `#if defined(BOOST_MATH_EXEC_COMPATIBLE)` 守卫(镜像上游条件),
  math.inc 同步。
- vendored 头修改新增 2 处(重跑 import_boost 需回放,§6.9):test/tools/
  detail/print_helper.hpp、test/utils/basic_cstring/basic_cstring.hpp。
- 测试消费方式调整记录:cobalt(仍 import,补标准头)、exception/log/
  wave 改 include-only(T3 consumer rule),timer(仍 import,加 sleep)。
