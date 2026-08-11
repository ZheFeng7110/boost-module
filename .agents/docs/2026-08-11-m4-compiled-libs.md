# M4 设计: 编译库接入 (8 库) + mcpp 源码配置

> 日期: 2026-08-11 · 状态: 已确认 (实施后修订) · 计划: boost-mcpp-module-plan.md M4
> 前置: M0 spike §4 (模块声明 ↔ 静态库定义链接模式) + M2 生成器 + M3 纯头模块层
> 实施结果: llvm/msvc + gcc/mingw 双风味 28/28 测试全绿

## 1. 目标

8 个编译库的 `libs/<lib>/src/*.cpp` 进 `mcpp.toml` sources, 与 19 个纯头库模块
一起构建成包; 模块 TU (头文件声明) ↔ 库 TU (定义) 链接一致 (M0 §4 已验证模式)。
统一 `-DBOOST_ALL_NO_LIB` + `-w` 压告警 — `[build]` 级 flags 对模块 TU 与库 TU
同源, 保证两侧宏/编译标志一致 (opencv BMI 基线标志教训)。

## 2. 每库编译策略

| 库 | 源码 (CMake 对照) | 说明 |
|---|---|---|
| filesystem | src/*.cpp 10 个 | 含 windows_file_codecvt.cpp (自守卫 `BOOST_FILESYSTEM_WINDOWS_API`, 全平台安全) |
| regex | src/{posix_api,wide_posix_api}.cpp 2 个 | regex v5 主体纯头, 编译部分仅 C-API 包装 |
| thread | src/future.cpp + 平台集 | **win32**: win32/{thread,tss_dll,tss_pe,thread_primitives}.cpp; **pthread**: pthread/{thread,once}.cpp。两集定义同名符号, 必须按平台互斥 |
| chrono | src/*.cpp 3 个 | 自 define `BOOST_CHRONO_SOURCE`; inlined/*.hpp 按特性宏自守卫 (无特性平台编译为空) |
| program_options | src/*.cpp 11 个 | 含 winmain.cpp (自守卫 `_WIN32`, posix 编译为空) |
| stacktrace | src/basic.cpp 1 个 | 见 §3 专用策略 |
| json | src/src.cpp 1 个 | 单 TU; src.hpp 顶部自 define `BOOST_JSON_SOURCE`; 模块 GMF **去掉** src.hpp (§4) |
| url | src/**/*.cpp 19 个 (7 + detail/8 + grammar/3 + grammar/detail/1) | CMake `GLOB_RECURSE src/*.cpp` 同集; 静态构建无需 BOOST_URL_SOURCE (DECL 为空) |

平台互斥: `[target.windows.build].sources` / `[target.unix.build].sources`
(不匹配平台的条件表整体不存在, 不会产生误匹配警告); 线程的 future.cpp 两平台共有, 放无条件表。

## 2a. 构建配置落地 (mcpp.toml, 实施后修正)

- **8 个 .cppm 进 sources** — M3 明确把 8 库留在 sources 外; M4 首批失败就是漏加
  (ninja 里 19 个模块, 8 个新模块完全不编译)
- `[build].defines = ["BOOST_ALL_NO_LIB", "_MT", "_WIN32_WINNT=0x0A00"]`
  - `_MT`: llvm/msvc 风味 clang++ driver 不定义线程标志, boost config 靠它判
    `BOOST_HAS_THREADS` (tss_pe.cpp 编译为空 → 链接缺 tss_cleanup_implemented)
  - `_WIN32_WINNT=0x0A00`: mingw 不默认定义, boost.winapi 的 WaitOnAddress/
    WakeByAddress* 需 >= 0x0602 才声明 (thread_primitives.cpp 依赖); 与生成器快照同值
- `[build].flags` per-glob: `{glob = "deps/boost/libs/thread/src/**",
  defines = ["BOOST_THREAD_BUILD_LIB"]}` — tss_pe/tss_null 的
  `tss_cleanup_implemented` 依赖该宏 (上游 b2/CMake 构建时定义), 只作用到 thread
  库源码, 不触及模块 TU
- 模块 TU 与库 TU 宏一致: 上述 defines 全部 package-wide (除 BOOST_THREAD_BUILD_LIB)

## 3. stacktrace 专用策略 — LINK + basic 固定

`boost/stacktrace/frame.hpp` 的关键分支 (frame.hpp:65): **未定义
`BOOST_STACKTRACE_LINK` 时头文件内联整套实现 (.ipp)** — 若模块 TU 不带 LINK,
模块 TU 自带全部内联实现, 与编译库重复且 BMI 膨胀。因此:

- 模块 TU (stacktrace.cppm GMF): `#define BOOST_STACKTRACE_LINK` → 头文件只留声明
- 库 TU: 只编译 `basic.cpp` (自 define `BOOST_STACKTRACE_INTERNAL_BUILD_LIBS` +
  `LINK`, 用 frame_unwind.ipp = 最简地址回溯实现, MSVC 走 CaptureStackBackTrace)
- **不编译** addr2line/backtrace/windbg*/noop/from_exception:
  与模块面固定 basic 一致, 免 dbgeng/ole32 外部依赖, posix/mingw 免 popen addr2line
- 代价: 消费者无法在模块面选实现 (模块接口宏固定, 与整体 feature-macro 限制一致)

## 4. json 模块 GMF 改造

- 原 GMF: `#include <boost/json/debug_printers.hpp>` + `<boost/json/src.hpp>`
  (M2 gate 保留 src.hpp 是为让生成器看到完整面)。M4 起定义落入库 TU (src.cpp):
  - **src.hpp 从模块 GMF 移除** — 否则模块 TU 与 src.cpp TU 双重定义
  - GMF 补 `<boost/json.hpp>` (src.hpp 曾代为引入全部声明)
- 库 TU: src/src.cpp 单文件, 自 define BOOST_JSON_SOURCE (src.hpp:20)
- **实施修正**: json.inc 必须重生成 — src.hpp 引入的 .ipp 声明了一批
  `boost::json::detail::*` 实体 (int64_formatter/parse_number_token 等), GMF 去
  src.hpp 后这些声明消失, 旧 .inc 无法编译。生成器新增 `GMF_OVERRIDE`
  (json → debug_printers.hpp + json.hpp, 与模块 GMF 完全一致), 快照与模块面同构
  (§10)。

## 5. filesystem v3/v4 决策

`boost/filesystem/config.hpp`: **`BOOST_FILESYSTEM_SOURCE` 是 API 切换开关** —
定义 → v4 版本命名空间 + `*_v4` 符号; 不定义 → v3 (`*_v3`)。上游 CMake 给库 TU
PRIVATE 传 SOURCE (v4), 但模块面 v3, 符号不匹配。

本包决策: **模块 TU 与库 TU 均不定义 SOURCE → v3 一致** (M0 spike 即此路径,
已实测链接通过; filesystem.inc 亦为 v3 快照)。上游 v4 新 API 不随模块面开放,
消费者无法自行开启 (模块宏固定), 列为已知限制。

## 6. mcpp.toml 变更

```toml
[build]
sources = [ 19 cppm + 8 cppm...,  # 8 个新 .cppm 必须进 sources (M3 留在外面)
  # M4 编译库 — 通用集 (各 .cpp 平台自守卫)
  "deps/boost/libs/filesystem/src/*.cpp",
  "deps/boost/libs/regex/src/*.cpp",
  "deps/boost/libs/chrono/src/*.cpp",
  "deps/boost/libs/program_options/src/*.cpp",
  "deps/boost/libs/stacktrace/src/basic.cpp",
  "deps/boost/libs/json/src/*.cpp",
  "deps/boost/libs/url/src/**/*.cpp",
  "deps/boost/libs/thread/src/future.cpp",
]
defines  = ["BOOST_ALL_NO_LIB", "_MT", "_WIN32_WINNT=0x0A00"]   # §2a
cxxflags = ["-w"]
flags = [{ glob = "deps/boost/libs/thread/src/**", defines = ["BOOST_THREAD_BUILD_LIB"] }]  # §2a

[target.windows.build]
sources = ["deps/boost/libs/thread/src/win32/*.cpp"]

[target.unix.build]
sources = ["deps/boost/libs/thread/src/pthread/*.cpp"]
ldflags = ["-pthread"]
```

- 线程平台文件用目录 glob (win32/ 与 pthread/ 各 4/3 文件, 目录内无多余 cpp —
  曾出现的 tss_null.cpp 位于 src/ 根, 不在平台子目录, 不会误入)
- 同名 basename 去重: filesystem/program_options 的 utf8_codecvt_facet.cpp 与
  url 的 error.cpp ×2 → mcpp 自动放到 `obj/boost_boost/...` 前缀目录, 无冲突

## 7. 手编偏离汇总 (.cppm)

| 文件 | 改动 | 理由 |
|---|---|---|
| json.cppm | GMF 去 src.hpp, 加 json.hpp | 定义移入库 TU, 防双定义 (生成器 GMF_OVERRIDE 同步) |
| stacktrace.cppm | GMF 加 `#define BOOST_STACKTRACE_LINK` | 头文件内联分支切到外部链接模式 (生成器 EXTRA_DEFINES 同步) |
| chrono/filesystem/system.cppm | export import 按重生成 .deps 收窄 (system/type_traits; system; variant2) | M2-era .deps 过期 |
| thread.cppm | export import 补 boost.optional | 重生成 thread.deps |
| url.cppm | export import mp11 → optional | 重生成 url.deps |
| scope.cppm / core.cppm / algorithm.cppm | M3 手编保持 (gcc ICE 变通 / 宏 re-homing / string.hpp 裁剪) | M3 §3, 重生成会覆盖, 见 §10 |

## 8. 验证计划 (实施结果)

1. llvm 20.1.7 / x86_64-windows-msvc: 27 模块 + 52 库 TU 构建 ✓, **28/28 测试绿**
2. 新增 8 个消费者 smoke 测试 (tests/{filesystem,regex,thread,chrono,
   program_options,stacktrace,json,url}.cpp), 覆盖符号级使用 (必须链接库 TU 定义):
   - filesystem: path/current_path/exists/create_directories/文件读写/remove_all
   - regex: regex_match/search/replace/iterator
   - thread: thread+mutex+future (join/wait_for, 防挂起)
   - chrono: steady/system_clock、duration 算术
   - program_options: split_unix + command_line_parser + variables_map
   - stacktrace: stacktrace() 捕获 + to_string 非空 + frame 地址
   - json: parse/serialize + object/value 访问 + 错误分支
   - url: parse + 组件访问 + encode/decode
3. gcc 16.1.0 / x86_64-windows-gnu: 构建 ✓, **28/28 测试绿** — M3 遗留的
   variant 消费者 gcc ICE 未再触发 (模块面重生成后消费 TU 变化), scope 变通保持

## 9. 已知限制 (M4 边界)

- filesystem 模块面 = v3 API (上游 CMake 库默认 v4), 见 §5
- stacktrace 实现固定在 basic (无 windbg/addr2line 符号名面)
- algorithm 模块的 *regex 实体裁剪 (M3 §3.3) 保持 — gcc 模块 TU abi-tag 冲突未解,
  M4 不改 (regex 库 TU 为普通编译, 不受影响)
- json/url/thread 等平台特性宏随构建期固定, 消费者不可自定义 (计划边界)
- boost.thread 模块面 = v2 API (BOOST_THREAD_VERSION 默认 2): 消费者见
  boost::unique_future (无 boost::future 名), 与上游默认一致 (M2 快照同源)

## 10. 生成器第三轮半 + 重放工具 (M4 落地, 防重生成丢失)

8 库的 .inc 是 **M2-era 快照** (无 M3 修复: CLASS_TEMPLATE/using-injection/typedef),
M4 全量重生成 27 库 (含 M3 的 19 库, 实体归属随之变动 — any.inc 82→21 等)。
配套改动:

1. **EXTRA_DEFINES** (gen_exports.py): 按库附加解析宏 — stacktrace 用
   `BOOST_STACKTRACE_LINK` 生成 (LINK 模式的 .inc 面 = 模块面, 否则 .ipp 内部
   实体 export using 落空)
2. **GMF_OVERRIDE**: json 的 GMF 覆盖为 debug_printers.hpp + json.hpp
   (与模块 GMF 同构, §4)
3. **curated 升级为跨模块覆盖**: curated/any.txt 补 typeindex 运算符集 —
   27-run first-wins 把 boost::typeindex::operator* 判给 variant, 但 any_cast
   模板体在消费者 TU 实例化需要它们从 boost.any 可达 (M3 时两模块都有, 合法重复导出)
4. **curated/filesystem.txt** (新): iterator_facade 的 ==/!= 是类内 friend 函数
   模板 — 非命名空间实体, 生成器不可见; 且 GMF 声明对消费者 ADL 不可见 →
   `it != end` 编译失败。用 curated 从模块面再导出
5. **thread.inc 平台守卫 ×6** (M3 §5 模式): mingw 快照含 gcc-only boost/atomic
   实体 (convert_memory_order_to_gcc, core_arch_operations_gcc_x86*,
   core_operations_gcc_atomic, fence_arch_operations_gcc_x86,
   fence_operations_gcc_atomic), MSVC ABI 下不存在
6. **scripts/reapply_hand_edits.py** (新): 一键重放全部手编 (M3/M4 .cppm 偏离 +
   .inc 守卫 + algorithm 恢复 + 其余 15 库 .cppm 注释头恢复), 幂等 —
   重生成后必跑 (gen_exports --emit-cppm → reapply_hand_edits.py)

## 11. 测试期教训 (与库无关的弯路)

- **stdout 缓冲**: 崩溃程序没 flush 的 stdout 输出丢失, 曾误导崩溃定位
  (po 排查时 puts 输出全丢 → 误判"崩在 main 之前")
- **program_options 语义**: 单值选项收到多值 → store() 阶段抛 multiple_values
  (value_semantic.cpp:122), 非 notify; 无效值同理在 store 抛 invalid_option_value。
  测试的 args 与异常捕获必须按此写
- **url API 拼写**: query() 返回 std::string (非 optional); params 迭代器
  operator-> 被 delete (用 *it); encode 签名是 (s, charset, opts, token);
  字符集对象是 grammar::all_chars / lut_chars (pchars 未导出)

## 12. 工作量

实际: 配置 + 3 处生成器增强 + 2 处 .cppm 手改 + curated ×2 + 重放脚本 + 8 测试,
两风味构建验证 (约 2 天, 含 po/url 排障)。
