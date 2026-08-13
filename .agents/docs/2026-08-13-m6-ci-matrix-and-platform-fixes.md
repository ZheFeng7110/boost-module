# M6 过程记录: GitHub Actions CI 矩阵 + 三平台适配 (M6–M7c)

> 日期: 2026-08-13 · 状态: **M6 完成 (CI 四腿全绿)** — 提交 bfd417a2 → a2db3cc4 (5 个提交)
> 计划: boost-mcpp-module-plan.md M6 · 前置: M0–M5 (27 库模块层 + 8 编译库 + 汇总模块)
> 验证: windows-llvm-msvc / linux-gcc / linux-llvm / macos-llvm 四腿全部 success
> (run 31701612021, 2026-08-13T12:46Z)

## 1. 目标

- 建立 GitHub Actions 三平台矩阵门禁: windows-llvm-msvc / linux-gcc / linux-llvm / macos-llvm。
- 把 M5 移交的三项 gcc/mingw 基线失败 (url/thread/variant) 与 CI 暴露的平台问题全部修复。
- 每个 job: checkout → 装 mcpp (pinned release, sha256 校验) → xlings 沙箱装工具链
  (actions/cache 按 job 缓存 ~/.mcpp) → `mcpp build` → `mcpp test` → examples `mcpp run`。
- **范围调整 (用户 2026-08-13)**: release 相关项 (mcpp-index 薄层 boost.lua / docs/architecture.md)
  不在本里程碑做 — 等后续把剩余库全部接入后再发布。

## 2. 实施内容

### 2.1 CI 矩阵 (.github/workflows/tests.yml, bfd417a2)

| 腿 | runner | 工具链 → 目标 | 结果 |
|---|---|---|---|
| windows-llvm-msvc | windows-latest | llvm@22.1.8 → x86_64-windows-msvc | ✅ |
| linux-gcc | ubuntu-24.04 | gcc@16.1.0 → x86_64-linux-gnu | ✅ (M7c 后) |
| linux-llvm | ubuntu-24.04 | llvm@22.1.8 → x86_64-linux-gnu | ✅ (M7b 后) |
| macos-llvm | macos-14 (arm64) | llvm@22.1.8 → aarch64-macos | ✅ (M7b 后) |

mcpp 安装: 从 GitHub Releases 下载 pinned `mcpp-2026.8.11.3-<plat>`, sha256 校验,
解压到 `~/.mcpp` 并加 PATH; 工具链经 mcpp xlings 沙箱 `mcpp toolchain install` 安装。
cache key 按 job 分开 (`mcpp-${{ matrix.os }}-${{ matrix.name }}`), 避免
linux-gcc / linux-llvm 之间的 toolchain default (config.toml) 互相污染。

### 2.2 修复轮次总览

| 提交 | 内容 | 解决的问题 |
|---|---|---|
| bfd417a2 | M6: CI 矩阵 | — |
| 301ce728 | M6: POSIX 平台守卫 (core/system/program_options/thread .inc + filesystem 测试) | 首轮 CI 全挂 (windows 除外) |
| a3495fc8 | M7: pthread once 伞文件 + arm64/x86 守卫 | linux 双腿链接挂 + macos Build 挂 |
| 5e010524 | M7b: clone_impl 显式实例化 / variant ICE / mac 异常 catch / libc++ println | macos Test 挂 + linux-gcc 挂 + linux-llvm example 挂 |
| a2db3cc4 | M7c: extern template 抑制 gcc 消费者 clone_impl 实例化 | linux-gcc thread 链接 (ELF 特有) |

失败收敛路径: run 31595247071 (四腿全挂) → 31599496213 (仅 windows 过) →
31684566063 (macos Build 过, linux 链接过) → 31689691819 (仅 linux-gcc thread 链接挂) →
31701612021 (**四腿全绿**)。

## 3. 平台问题根因与修复 (按提交)

### 3.1 M6 (301ce728): mingw 风味快照 × POSIX 平台 (首轮全挂根因)

`scripts/gen_exports.py` 在 Windows 生成 `.inc` — 快照是 mingw 风味, 含仅 Windows
存在的实体; POSIX 下 `_WIN32`/`BOOST_WINDOWS_API` 未定义时这些实体不存在 → 模块 TU 编译失败。

守卫清单 (全部经 `scripts/reapply_hand_edits.py` 重放, 幂等):

- `core.inc`: `sp_thread_sleep`/`sp_thread_yield` — Windows 下在 `boost::core::detail`,
  POSIX 下在 `boost::core` (nanosleep/sched_yield 分支), `#if defined(_WIN32)||__WIN32__||__CYGWIN__` 二选一。
- `system.inc`: 5 个 detail 实体 (`local_free`/`message_cp_win32`/`system_category_condition_win32`/
  `system_category_message_win32`/`unknown_message_win32`) 加 `BOOST_WINDOWS_API` 守卫;
  `windows_error` 整块 + `boost::winapi` 整块加 `_WIN32` 守卫。
- `program_options.inc`: `split_winmain` 加 `_WIN32` 守卫 (winmain.hpp 仅 Windows 进 GMF)。
- `thread.inc`: `boost::detail::win32` 块、`win32::detail` 块、`boost::winapi` 块整体守卫;
  约 30 个散落 Windows-only 实体 (`intrusive_ptr`/`wait_operations_windows`/`time_from_ftime`/
  `interruptible_wait`/win32 once/mutex/interlocked 系列) 经新助手 `guard_entity_lines()` 逐行守卫。
- `tests/filesystem.cpp`: `file_size == 22` (字面量 22 字节, 原断言 21 错);
  `if (create_directories(...))` 在目录已存在时静默跳过整个块 → 改
  `assert(create_directories(dir,ec) || exists(dir,ec))` (CI 全新 runner 暴露, 本地重复运行掩盖);
  ofstream/ifstream/directory_iterator 加作用域块再 `remove_all` (Windows 开着的句柄阻塞删除)。

机制提醒: 该工具链组合 (llvm/msvc) 不发 GNU depfile — 编辑模块接口 purview 内 include 的
`.inc` 不会触发重建, **验证前必须 `mcpp clean --bmi-cache`** (本轮所有验证均如此)。

### 3.2 M7 (a3495fc8): pthread once 伞文件 + 架构守卫

**linux-gcc / linux-llvm 测试全挂 — `duplicate symbol: thread_detail::*once_region*`**
(84 处日志, 所有 28 个测试二进制):

`libs/thread/src/pthread/once.cpp` 是**伞文件** (第 8 行 `#include "./once_atomic.cpp"`),
上游 b2/CMake 只编译 once.cpp。`mcpp.toml` 的 glob `pthread/*.cpp` 把 once_atomic.cpp
又当作独立 TU 编译 → 每个测试二进制两份强定义。修法: `[target.unix.build]` sources
改为明确列表 `once.cpp` + `thread.cpp`。win32 侧无伞文件, 不受影响 (windows 腿本来就绿)。
验证: musl 交叉构建产物 libboost.a 中三个符号仅在 once.o 定义一次。

**macos-llvm Build 挂 — thread.inc 三个 x86 实体不存在 (arm64)**:

`core_arch_operations_gcc_x86`/`_x86_base`/`fence_arch_operations_gcc_x86` 是 boost/atomic
`gcc_x86` 后端 (platform.hpp: `__GNUC__ && (__i386__||__x86_64__)`) 才有; macOS arm64 用
`gcc_aarch64` 后端。原 `#if defined(__GNUC__)` 守卫在 clang 下**也成立** (clang 兼容定义
`__GNUC__`) → 仍导出 → 报错。改成完整镜像后端条件 `__GNUC__ && (__i386__||__x86_64__)`。
(坑: 裸架构条件在 x86_64-windows-msvc 下会误导出 — clang-cl 定义 `__x86_64__` 但不定义
`__GNUC__`, msvc ABI 下这些实体不存在; 本地踩到后修正为完整条件。)

**macos-llvm Build 挂 — url.inc 两个 SSE2 实体**:

`find_if_pred`/`find_if_not_pred` (grammar/detail/charset.hpp) 只在
`BOOST_URL_USE_SSE2` (x86 + SSE2) 下定义; 加 `#if defined(BOOST_URL_USE_SSE2)` 守卫。

### 3.3 M7b (5e010524): 四个平台问题

**linux-gcc thread 链接挂 — clone_impl 虚拟 thunk undefined** (M5 移交项):

`clone_impl<T>` (boost/exception/exception.hpp) 虚继承 `clone_base` → vtable 需要
virtual/non-virtual thunk (clone/rethrow/~clone_impl)。gcc 16.1.0 模块消费者 TU
引用这些符号但从不发射。修复: 新增 `src/boost_thread_extras.cpp` (M5
`boost_system_extras.cpp` 同模式) — 对三个可达特化 (`broken_promise`/`unknown_exception`/
`std_exception_ptr_wrapper`) 显式实例化, vtable+thunk 单份落入库 TU。
验证: musl 产物 extras.o 含全套 `_ZTv0_n*` (vcall) / `_ZThn40_*` (non-virtual) thunk +
`_ZTV` vtable。mingw 下该提交后 thread 链接通过 (运行挂起是 win32 实现本地问题, 见 §5)。

**linux-gcc variant 测试挂 — gcc 16.1.0 ICE** (M5 移交项):

`tests/variant.cpp` 的 `boost::apply_visitor(visitor(), v)` 在消费者 TU 触发
`has_result_type.hpp:25` Segmentation fault — 自由函数 `apply_visitor` 的两个重载
(C++03 版与 C++14 版) 都经过 `has_result_type<Visitor>` 实例化 (disable_if 签名), 无论
visitor 形态, gcc 模块消费者必崩。改测试用**成员版本** `v.apply_visitor(vs)` (同一分发
语义, 内部走 visitation_impl, 不经 has_result_type)。mingw 本地复现并验证 ICE 消失。

**macos-llvm Test 挂 — program_options 异常未捕获**:

库 TU 经 `boost::throw_exception` 抛出 `wrapexcept<invalid_option_value>` (boost.exception
包装), 测试 catch `po::invalid_option_value const&` 落空 → terminate (exit 134)。
根因: macOS (Mach-O) 不按 ELF/PE 方式 COMDAT 合并模块跨边界的 typeinfo — 库 TU 与模块
消费者看到不同的 boost.exception 继承树 typeinfo, 精确 catch 无法匹配 (libc++ type_info
按指针比较)。Linux (ELF weak COMDAT 合并) 与 Windows (PE COMDAT) 均正常。修复: 测试
catch 增加 `std::exception const&` 兜底 (libc++ 单份定义, 仍在 wrapexcept 继承链上)。

**linux-llvm example 挂 — std::println 无法编译 (libc++ 22.1.8)**:

`import std;` + `std::println("...", args)` 实例化 `formatter<basic_format_string<...>>`
(隐式删除默认构造) — libc++ 22.1.8 x86_64-linux 下格式串被当格式化参数处理。
Windows 用 MSVC STL 正常。修复: examples 全部改用 `std::printf` (libc++/MSVC STL
均成熟支持)。macOS example 上轮被 skip 未暴露, 一并换掉。

### 3.4 M7c (a2db3cc4): ELF COMDAT 冲突 — 最终修复

M7b 后 linux-gcc 仍挂 thread 链接, 但缺的 thunk 与 extras.o 中已有符号 demangle 完全一致,
musl/mingw 产物也验证全套 thunk 存在。排查:

- mcpp 测试链接为**对象平铺** (rsp 含全部 .o, 含 extras.o), 非 archive 提取 — 排除未参与链接。
- mingw (PE/COFF) 链接成功、glibc (ELF) 失败 — 平台差异在 COMDAT 处理: PE 每个 COMDAT
  独立解析; **ELF 按 COMDAT group 去重, 只保留首个同组对象**。
- 消费者 TU (thread.o) 仍隐式实例化 clone_impl (gcc 模块实现让 GMF 定义"可见"),
  发射**自己的** weak vtable (组名 `_ZTVN...clone_impl...`) 且**不含 thunk** (gcc 模块
  消费者从不发射 thunk); 该组先于 extras.o 的同名组被链接器保留 → vtable 槽悬空。

修复: **extern-template 显式实例化声明**放入 boost.thread 模块接口 (thread.inc):
`extern template class clone_impl<broken_promise/unknown_exception/std_exception_ptr_wrapper>;`
— 消费者看到后**抑制隐式实例化**, 只引用 extras.o 的 vtable+thunk, 不再自产残缺 vtable。
验证 (mingw gcc 16.1.0, 与 CI 同编译器): `tests/thread.o` 只剩 `.refptr._ZTV...` 外部
引用, 零 clone_impl 成员定义; llvm/msvc 28/28 与 musl 交叉构建无回归。

## 4. 本地验证手段 (Windows 宿主的限制与对策)

- **默认工具链**: llvm@22.1.8 (x86_64-windows-msvc) — `mcpp test` 28/28 全绿,
  examples `mcpp run` 全过 (每轮修复后回归)。
- **mingw gcc 16.1.0** (x86_64-windows-gnu): 与 CI linux-gcc 同一编译器, 用于复现
  gcc 平台问题 (variant ICE / clone_impl thunk); 基线 25/28 → 修复后 26/28
  (thread 运行挂起 + url 为本地 win32 特有, 见 §5)。
- **musl 交叉编译** (`mcpp build --target x86_64-linux-musl`): POSIX 编译路径 + 链接
  符号检查 (nm: once_region 单定义、extras.o thunk 齐全)。
- 无法本地运行 Linux ELF/macOS 二进制 → 测试运行阶段结果依赖 CI (musl 工具链无
  std 模块, 交叉测试不可行)。
- `nm`/`readelf -g` 符号级验证: COMDAT group 归属、vtable/thunk 定义位置。

## 5. 已知限制与遗留 (非 CI 阻塞)

- **mingw 本地 thread 运行挂起**: `boost::this_thread::sleep_for` 在 win32 实现
  (interruptible_wait + WaitableTimer) 下挂死 (定位至 sleep_for 处)。CI 无 mingw 腿,
  pthread 实现 (condition_variable.timed_wait) 正常; 属 win32 模块化运行时问题, 留待
  mingw CI 里程碑。
- **mingw url 测试失败**: M5 基线 (BOOST_URL_RETURN_EC 宏静态冲突), 未在本里程碑处理
  (CI 无 mingw 腿)。
- **gcc 模块消费者 × 自定义异常**: extern template 只覆盖三个库内特化; 消费者把
  **自定义异常类型** (copy_exception(MyError())) 包成 clone_impl<MyError> 时, gcc
  消费者仍缺 thunk (编译器 bug 的残余面), 非 CI 覆盖路径, 记录在案。
- **macOS 精确异常类型 catch**: program_options 测试以 std::exception 兜底,
  平台 typeinfo 分裂的根治 (Mach-O typeinfo 合并) 超出本项目范围。
- **mcpp depfile 缺失**: 编辑 .inc 等 purview 内 include 文件后必须
  `mcpp clean --bmi-cache`, 否则复用陈旧 BMI/对象 (本轮全部验证均遵守)。

## 6. 后续

- 剩余库全量接入 (当前 27 库; 边界宏驱动库如 preprocessor/mpl/fusion/proto/spirit/
  xpressive/lambda/bind/typeof 的接入策略评估)。
- 特性宏构建期固定问题 (asio/locale/log/context 等) 的 feature 里程碑设计。
- 发布: mcpp-index 薄层 boost.lua + docs/architecture.md + release 流程
  (**用户指定: 等剩余库接入后统一做**)。
