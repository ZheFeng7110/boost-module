# MinGW sysroot 一键引导 (scripts/fetch_mingw_sysroot.py)

> 日期: 2026-09-19 · 状态: 已实现 · 分支 `b1.91.0wdev`
> 关联: `scripts/boost_common.py` 的 `GEN_TARGET` / `GEN_SYSROOT`；
> `.agents/docs/2026-09-17-variable-template-export.md` §3.4

## 1. 背景

`scripts/gen_exports.py` 用 libclang + 真实 `clang++` 驱动，以
`--target=x86_64-w64-mingw32` 复现已提交的 mingw 风味 `src/gen_exports/*.inc`
快照（`boost_common.GEN_TARGET`）。生成器只做 `-fsyntax-only` 与 AST 解析，
**从不链接**，因此它需要的只是目标平台**头文件**（mingw-w64 CRT + GCC
libstdc++），并不需要 MinGW 的 gcc/ld/binutils。

实际痛点：

- 维护机（非 Windows）没有 mingw sysroot 时，默认 mingw target 的 gate 与
  libclang parse 会因找不到头文件而失败，只能改用 host target
  （`.agents/plan/2026-09-19-var-template-initializer-deps.md` §4），
  无法复现已提交快照。
- 此前 `BOOST_MODULE_GEN_SYSROOT` 只能由使用者手动指向一份"本地解包"的
  sysroot，来源、版本、校验都没有固化。

结论（2026-09-19）：在 `scripts/` 下新增引导脚本，把固定版本的 sysroot
下载到 `scripts/_deps/`（gitignored），作为脚本开发环境的一部分。

## 2. 决策

- **固定源**：WinLibs `winlibs-x86_64-posix-seh-gcc-16.1.0-mingw-w64ucrt-14.0.0-r4`
  （即本地开发一直使用的 GCC 16.1.0 / mingw-w64 14.0.0 / UCRT 风味）。
  与已提交快照同源，避免头文件演进导致 `.inc`/`.deps` 伪 diff。
- **产物位置**：`scripts/_deps/`，加入 `.gitignore`。
- **自动集成**：无显式 `BOOST_MODULE_GEN_SYSROOT` 时，默认 mingw triple
  统一使用 `scripts/_deps/` 下的 sysroot（见 §5）。
- **三平台可用**：Linux / macOS / Windows 均可下载解包（纯 stdlib + 可选
  外部 7z）。
- **压缩格式优先级**：7z > tar.xz > zip/tar.gz。WinLibs 只提供 `.7z` 与
  `.zip`；Python 无原生 7z，故优先复用可用的 7z 后端，否则回退 `.zip`。
- 不接入 CI（仅本地开发引导）。

## 3. 脚本设计 (`scripts/fetch_mingw_sysroot.py`)

### 3.1 固定清单

`ARCHIVES` 固化每个归档格式的 `(filename, sha256)`；`_BASE` 由固定 tag
拼出 GitHub Release URL。sha256 取自上游 `<asset>.sha256` 文件：

| 格式 | 大小 | sha256 (前 12) |
|---|---|---|
| `.7z`  | ~105 MiB | `08b46777f127` |
| `.zip` | ~260 MiB | `c406a22f8cac` |

版本是**快照契约的一部分**：升级 WinLibs/mingw-w64/libstdc++ 会改变 Boost
条件编译分支，进而改变生成物。升级必须同步更新 sha256，并重跑全量生成 +
`reapply_hand_edits.py` 复核。

### 3.2 归档后端探测

`_sevenzip_backend()` 依次探测 `py7zr` → PATH 上的 `7z`/`7za`/`7zr`。
`pick_format("auto")` 在有任一后端时选 `.7z`，否则选 `.zip`。显式
`--archive 7z` 在后端缺失时报错并提示 `--archive zip`。若未来引入
tar.xz 源，`_extract_tar` 已通过 stdlib `tarfile` 支持（含 xz/bz2/gz/zst）。

### 3.3 下载（并行 range + 单流回退）

GitHub Release CDN 对单连接限速严重（实测 ~40 KiB/s），而多连接 range
可达数倍。因此：

- `_head_total()` 取 `Content-Length`；
- 体积 > 8 MiB 且 `--jobs > 1`（默认 8）时走 `_parallel_stream()`：按字节
  区间切 N 块，`ThreadPoolExecutor` 并发下载到 `<dest>.partN`，带锁聚合
  进度，最后顺序拼接为 `dest`；
- 任一 chunk 失败 / 服务端忽略 `Range`（非 206）则抛异常，回退
  `_single_stream()`；
- 下载前先查缓存：`dest` 存在且 sha256 匹配即跳过（`--force` 强制重下）。

### 3.4 安全解包

`_safe_join()` 对每个归档成员做路径穿越检查（拒绝绝对路径、盘符、`..`
逃逸出目标目录），zip/tar 统一先校验成员列表再 `extractall`；tar 额外优先
使用 `filter="data"`（py≥3.12）。7z 走 `py7zr` 或 `7z x`。

### 3.5 sysroot 定位与 probe

WinLibs 解包后顶层为 `mingw64/`，目标树在其下。`find_sysroot()` 以
`<root>/x86_64-w64-mingw32/include/windows.h` 为标志，先检查
`scripts/_deps` 本身，再按 1–3 层 glob 扫描。

`probe()` 用 `clang++ --target=x86_64-w64-mingw32 --sysroot=<root>
-std=c++23 -fsyntax-only` 编译一段包含 `<windows.h>`、`<cstddef>`、
`<string>`、`<vector>` 的 TU，验证 CRT 头与 libstdc++ 均能解析。
`clang++` 不在 PATH 时打印警告并跳过（不作为失败）。可用 `--no-probe`
显式跳过。

### 3.6 marker

成功后写 `scripts/_deps/mingw-sysroot.json`：

```json
{ "version": "...", "target": "x86_64-w64-mingw32",
  "root": "scripts/_deps/mingw64", "archive": "7z", "sha256": "..." }
```

`current_root()` 优先读 marker，失效则回退文件系统扫描。

### 3.7 命令行

```
uv run scripts/fetch_mingw_sysroot.py            # 下载 + 校验 + probe
uv run scripts/fetch_mingw_sysroot.py --archive zip   # 强制 zip
uv run scripts/fetch_mingw_sysroot.py --jobs 16      # 并发连接数
uv run scripts/fetch_mingw_sysroot.py --check        # 只 probe 现有树
uv run scripts/fetch_mingw_sysroot.py --print-path   # 打印 sysroot 根
uv run scripts/fetch_mingw_sysroot.py --force        # 重新下载
```

## 4. `.gitignore`

新增 `scripts/_deps/`（与既有 `scripts/_gen_exports-cache/` 并列）。

## 5. `boost_common.py` 集成

`GEN_TARGET` 默认仍为 `x86_64-w64-mingw32`（快照风味不变）。sysroot 解析
优先级：

1. `BOOST_MODULE_GEN_SYSROOT` 环境变量（显式覆盖，最高优先级）；
2. 未设置且 `GEN_TARGET` 等于默认 mingw triple 时，自动探测
   `scripts/_deps/`（marker → 文件系统扫描）并使用；
3. 其他情况（`BOOST_MODULE_GEN_TARGET` 被改成 host/cross）不自动套用
   mingw sysroot，除非显式给出 `BOOST_MODULE_GEN_SYSROOT`。

探测逻辑在 `boost_common._bundled_sysroot()` / `_looks_like_sysroot()`；
`--sysroot` 仅通过既有 `TARGET_ARGS` 注入，因此 libclang parse 与 clang++
gate 自动一致。

## 6. 验证

`scripts/_deps/` 为本地生成物，验证不入库。已在 Linux (Homebrew clang 22,
无系统 mingw) 上实测：

- 脚本端到端：下载 `.7z` → sha256 通过 → 解包到 `scripts/_deps/mingw64`
  （顶层 `mingw64/`，含 `x86_64-w64-mingw32/include/windows.h`、
  `include/c++/16.1.0`、`lib/gcc/x86_64-w64-mingw32/16.1.0`）→ probe 通过
  → 写出 marker。
- 二次运行命中缓存并 probe；`--print-path` / `--check` 正常。
- `BOOST_MODULE_GEN_SYSROOT` 显式覆盖优先；`BOOST_MODULE_GEN_TARGET`
  改为 `x86_64-linux-gnu` 时不套用 mingw sysroot（`TARGET_ARGS` 无
  `--sysroot`）。
- **生成器复现**：以 `LIBCLANG_PATH=<full-LLVM>/lib` 运行
  `gen_exports.py --libs config assert throw_exception core type_traits
  --out /tmp/…`，`assert.inc` / `throw_exception.inc` / `type_traits.inc`
  及五个 `.deps` 与已提交快照 **byte-identical**；`config.inc` / `core.inc`
  仅差已知手编 guard（由 `reapply_hand_edits.py` 回放），证明下载的
  WinLibs GCC 16.1.0 sysroot 与已提交快照同源。

> 注：libclang 必须来自完整 LLVM（带 `lib/clang/<ver>/include`）；PEP 723
> 的 pip `libclang` wheel 不带 resource dir，会导致 `<malloc.h>` → `mm_malloc.h`
> 解析告警、std 面退化。用 `LIBCLANG_PATH=<full-LLVM>/lib` 指向完整 LLVM 即可
> （本机为 Homebrew llvm@22）。

## 7. 取舍与限制

- **只覆盖生成环境**：库的构建/测试本来就不需要 mingw（CI 三平台腿 +
  host 工具链），本脚本只服务 `scripts/` 的 mingw 风味快照复现。
- **版本强绑定**：sha256 与版本是硬编码契约；升级需同步重生成并复核
  `reapply_hand_edits.py` 的平台守卫。
- **网络**：GitHub CDN 单连接与地区相关；脚本用并发 range 缓解，但无
  镜像/代理配置。`--jobs 1` 可退回单流。
- **7z 依赖**：默认 `.zip`（stdlib）；更小的 `.7z` 需要 `py7zr` 或系统
  `7z`，未内建为强依赖以免拖累 `uv run`。
- **不替代 native mingw 编译**：若将来需要 mingw 目标的实际编译/链接，
  该 sysroot 缺 `.a`/binutils，仍需完整工具链。

## 8. 涉及文件

- 新增 `scripts/fetch_mingw_sysroot.py`
- 修改 `scripts/boost_common.py`：
  - bundled sysroot 自动解析（`_bundled_sysroot` / `_looks_like_sysroot`）；
  - 顺带修复 `load_libclang` 的 `LIBCLANG_PATH` 目录形态：原先只认
    `libclang.dll`，在 Linux/macOS 上会把目录误当文件传给
    `set_library_file` 而报错；现用 `_libclang_in()` 识别
    `.dll` / `.so[.N]` / `.dylib`，三平台目录形态均可用（同时让
    `_append_resource_dir` 能定位资源目录）。
- 修改 `.gitignore`（`scripts/_deps/`）
- 更新 `docs/architecture.md` / `docs/zh/architecture.md` §6
