# macOS CI 失败根因:mcpp 上游已知未修的 build.mcpp host-link 缺陷

日期:2026-08-16 · 基线:boost-module `6afd83ce`、mcpp HEAD `f4b64a1`(v2026.8.15.3)

起因:M8 引入 `build.mcpp` 后,`macos-llvm` CI 腿在 `mcpp build` 的第一步(编译 `build.mcpp` host helper)即失败。将 CI 中的 mcpp 版本从 2026.8.11.3 抬升到 2026.8.15.2 后依然失败,故展开本次根因分析。

---

## 1. 现象

`tests.yml` `macos-llvm` 腿,`mcpp build` 步骤,`build.mcpp compiling` 之后立即失败:

```
error: build.mcpp failed to compile (exit 1):
dyld[5701]: Symbol not found: __ZdaPv
  Referenced from: <…> /Applications/Xcode_15.4.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/ld
  Expected in:     <…> /Users/runner/.mcpp/registry/data/xpkgs/xim-x-llvm/22.1.8/lib/libc++.1.0.dylib
clang++: error: unable to execute command: Abort trap: 6
clang++: error: linker command failed due to signal (use -v to see invocation)
```

- 被 abort 的是 **Apple 自己的链接器 `/usr/bin/ld`**(Xcode 15.4),不是 clang++,也不是我们的程序。
- `__ZdaPv` 是 `operator delete[](void*)` 的 mangling;dyld 期望它在 **llvm 22.1.8 payload 的 libc++** 里,但那份 libc++ 没有。
- 主构建(27 库)在 macOS 上**全绿** —— 只有 build.mcpp 的 host 链接这一步挂。

## 2. 结论(先行)

**这是 mcpp 上游已知、已记录、至今未修的缺陷**,与 boost-module 的 mcpp 版本无关。对应 mcpp 仓库自身的记录:

`.agents/docs/2026-08-13-build-optimization-status.md` §9a "macOS 上 mcpp 编不了依赖的 `build.mcpp` 助手" 及 §9a-2 "同一个机制,更大的面"。

错误签名与我们的 CI 一字不差(§9a 原文):

```
error: dependency 'xpkg': build.mcpp failed to compile (exit 1):
dyld[21445]: Symbol not found: __ZdaPv
clang++: error: unable to execute command: Abort trap: 6
```

**因此「抬高 mcpp 版本」从原理上就不可能解决**:修复从未进入任何 release(见 §6)。

## 3. 根因链(基于当前 mcpp 源码重推)

1. boost-module 仓库根有 `build.mcpp`(含 `import mcpp;`)。`mcpp build` 在 prepare 阶段用 **host 工具链**(llvm@22.1.8)编译并链接它(`build_program.cppm::run_build_program`)。
2. 这条 host 链接的 flag 由 `mcpp.toolchain.hostflags` 单一生产者装配:
   - `build_program.cppm:154` 把 host helper 的 `cfgBypass` 设为 `CfgBypass::LinuxOnly`;
   - `hostflags.cppm:177-185` 里 `bypassCfg = dm.hasCfg && (Always || is_linux)` —— macOS 上为 false → 命中 `else if (dm.hasCfg) return out;`(:184)**返回空 link token**:没有 `-fuse-ld=lld`,也没有 `-L`/`-rpath`。
3. 于是 clang++(payload)用**默认链接器** = Xcode 的 `/usr/bin/ld`。
4. Apple 的 `ld` 自身是 C++ 写的 Mach-O、**链接了 libc++**;dyld 启动它时,把它自己的 libc++ 依赖解析到了 **llvm 22.1.8 payload 的 `libc++.1.0.dylib`**(loader 搜索路径被 `DYLD_*` 污染,mcpp/xlings 为了让 payload 二进制可运行而设,所有子进程继承),而这份 libc++ 缺 `__ZdaPv` → dyld 在 `ld` 启动阶段就 abort,还没开始链接。

判据(mcpp bench 的实测,§9a-2):去掉 macOS 上所有 payload libc++ flag 后**照样发生** → 污染经由 `DYLD_*` 环境进入、被所有子进程继承,**不是链接 flag**。

## 4. 为什么主构建不受影响

macOS 主构建**刻意不用 Xcode 的 ld**,而是 `-fuse-ld=lld`:

- `flags.cppm:1059-1063` 注释原文:*"linker — use LLVM's own lld … instead of Xcode's ld: the system ld's version floats with the host Xcode (observed: Xcode 15.4's ld aborting at launch on macos-14 CI when its libc++ resolution was diverted), and lld ships with the exact toolchain doing the compile."*
- 链接行在 `flags.cppm:1085`:`… -fuse-ld=lld …`。

同一台 runner、同一个 payload,`lld` 能用而 Xcode `ld` 不能 —— 这就是「换 lld 即可过」的直接证据,也是 §3 里 host 链接漏掉 `-fuse-ld=lld` 成为唯一差异点的原因。

## 5. 为什么三个链接器行为不同

| 链接器 | 来源 | 自身链接的 libc++ | 在 DYLD_* 污染下 |
|---|---|---|---|
| `/usr/bin/ld`(Xcode 15.4) | 系统 | 系统 libc++(期望 `/usr/lib/libc++.1.dylib`) | dyld 把它的 libc++ 解析到 payload libc++ → 缺 `__ZdaPv` → 启动即 abort |
| `ld64.lld` / `lld` | llvm payload | payload libc++,配对一致 | 正常运行 |

bench 结论(§9a-2):"被测的 mcpp 那条臂 18 个格子全绿 —— 三个引擎同样地挂、一个不挂,说明问题在环境而不在任何一个引擎",而 mcpp 臂恰好全程用 lld。

## 6. 为什么「抬高 mcpp 版本」无效

- 缺陷记录于 2026-08-13(mcpp `fadd78d` 起的文档);截至 v2026.8.15.3 / HEAD `f4b64a1`,`hostflags.cppm`、`build_program.cppm`、`post_install.cppm` 的 macOS host-link 路径**零改动**。
- mcpp bench 团队对 macOS 的做法是直接**排除格子**(`0ae60f1`,写在 matrix.json 里),没有修 mcpp 本体 —— 文档明说"本机是 Linux,复现不了,而这一条已经烧掉好几轮 CI"。
- 我们 CI 从 2026.8.11.3 抬到 2026.8.15.2:中间版本(8.13 bench 系列、8.15.1/2/3)都没有修这条路径。

## 7. 修复方向(记录,待决策)

### A. mcpp 侧(治本,推荐)
让 build.mcpp 的 host 链接在 macOS 上对齐主构建的 lld 用法。两个落点:
- `hostflags.cppm::host_link_tokens` trustCfg 分支:对 macOS 追加 `-fuse-ld=lld`(等价于主构建 `flags.cppm:1085` 的做法);
- 或 `post_install.cppm::fixup_clang_cfg` macOS 分支:把 `-fuse-ld=lld` 写进 cfg。

生效方式:从源码构建 patched mcpp 供 CI 使用(或上传自建 release/artifact),而不是下载官方 release 二进制。也可向 mcpp 上游提交 / 跟踪该缺陷。

### B. CI 层环境中和(治标,需实测)
`mcpp build` 前清空 `DYLD_LIBRARY_PATH` / `DYLD_FALLBACK_LIBRARY_PATH`。前提:污染不是由 mcpp 在子进程内重新注入;风险:payload 二进制可能因此找不到自己的 libc++。需在真实 runner 上验证,不确定。

### C. 等上游修复
不可控;可作为长期跟踪项(mcpp §9a / 相关 issue),不作为唯一手段。

## 8. 相关坐标

| 位置 | 内容 |
|---|---|
| `mcpp/src/build/build_program.cppm:150-168` | host helper 的 `HostFlagOptions`,`cfgBypass = LinuxOnly`(:154) |
| `mcpp/src/toolchain/hostflags.cppm:168-206` | `host_link_tokens`;trustCfg 分支 :183-185 `return out;`(空) |
| `mcpp/src/build/flags.cppm:1047-1090` | macOS 主构建链接行,`:1085` `-fuse-ld=lld`;`:1059-1063` 注释 |
| `mcpp/.agents/docs/2026-08-13-build-optimization-status.md` §9a / §9a-2 | 上游已知缺陷记录(与我们的错误一字不差) |
| `mcpp` `df67537` / `0ae60f1` | bench 侧修 harness、排除 macOS 格子,未修 mcpp 本体 |
| `.github/workflows/tests.yml` | `macos-llvm` 腿,`MCPP_VERSION` env |
