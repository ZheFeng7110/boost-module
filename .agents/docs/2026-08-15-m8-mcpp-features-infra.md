# M8 — mcpp features 基建 + 生成器全库化

> 日期: 2026-08-15 · 里程碑: M8 (`boost-mcpp-all-libs-features-plan.md` §4)
> 前置: M0–M7 (27 库接入, CI 四腿全绿) · 本文记录实现与验证过程

## 1. Spike 验证结论 (build.mcpp 生成汇总模块)

M8 首日做的高风险项: **build.mcpp 动态生成 `import boost;` 汇总模块**,
验证"扫描 / 打包进 lib / 消费者 import"三连。使用临时工程逐一验证:

| 验证点 | 结果 |
|---|---|
| build.mcpp `mcpp::source(out_dir/agg.cppm)` 生成 `export module` 被 modgraph 扫描 | ✅ 编译并进入 lib |
| 本包 TU / tests 可 `import` 生成模块 | ✅ |
| **消费者** (独立工程, path dep) 可 `import` 生成模块 | ✅ `mcpp run` 通过 |
| 生成模块内容随 feature 集变化 (ctxHash 失效重跑) | ✅ `--features b` 后内容含 b |
| `default-features = false` + `features=["b"]` 消费者只拿到 b | ✅ 用 a 的实体报错 |
| feature-gated 源 `[features.X].sources` 未激活不编译 | ✅ |
| test 模式 (includeDevDeps) DROP 跳过: 非激活 feature 源**不编译** | ✅ (见 §1.1) |
| thread 式 per-OS 互斥 (`!` 排除 + feature 全平台 glob) | ✅ 仅目标平台 TU 编译 |

结论: 计划 §3.3 方案可行, 无需回退静态汇总。build.mcpp 用 `import mcpp;`
typed API (`has_feature` / `source` / `out_dir`), 生成文件放 `out_dir/`,
`mcpp::source()` 绝对路径 (root 与 dep 两种身份都正确)。

### 1.1 test 模式语义 (实测, 修正计划 §1.8 的推断)

`mcpp test` (includeDevDeps) 下 DROP 跳过但 ADD 保留 (prepare.cppm L4049/L4053):
- 若 per-lib 源**只在 feature `sources`**、base 不含 → test 模式只编译激活 feature 源
  (非激活库模块缺失, 对应测试须 `--features`)。计划 §1.8 描述的是这一形态。
- 但 **`[build].sources = []` 会触发 mcpp 的 `src/**` 推断** (toml.cppm L1475),
  推断 glob 落入 base → test 模式 DROP 跳过时全量编译, 分组测试失效。
- **实测采用**: base `[build].sources` 保留全部 per-lib glob (含编译库 TU), 每库
  feature `sources` 用**相同字符串**声明 gating。于是:
  - `mcpp build` (build 模式): DROP 按字符串剔除未激活库 → 默认 18 库模块编译; `--features all` → 27。
  - `mcpp test` (test 模式): DROP 跳过 → 全量编译 → 27 库测试默认全绿;
    `mcpp test --features <组>` 亦全绿 (additive, 组测试为 CI 显式分组)。
  - 汇总模块 `boost.cppm` 由 build.mcpp 按激活 feature 生成, 空壳也合法。

> 偏差记录: 计划 §1.8 "非激活 feature 源不编译(测试须 --features)" 仅在 feature-only
> sources 形态成立; 该形态因 `sources=[]` 触发 src/** 推断而不稳定 (实测)。base 保留
> per-lib glob 使默认 `mcpp test` 全绿 (27 库), `--features` 分组测试仍作为显式验证。

## 2. mcpp.toml 重构

### 2.1 结构

```
[build]
# 每库源 glob 保持在此 (feature 的 sources 与 base 相同 glob 声明 gating) —
# ⚠ 实测: sources 清空会触发 mcpp 的 src/** 推断 (toml.cppm L1475), 使 test
# 模式 DROP 跳过时全量编译, 破坏按 feature 分组测试; 故 base 保留全部 per-lib
# glob (含编译库 TU), 不依赖推断。
sources = [ ... 27 库 glob (同现状) ... ]
include_dirs / defines / cxxflags 不变
flags = []                      # thread 的 BOOST_THREAD_BUILD_LIB 移入 feature thread.flags

# ── <gen-features> 由 scripts/gen_features.py 生成, 勿手改 ──
[features]
default = [18 库闭包]            # any algorithm chrono core filesystem io iterator json
                                # mp11 optional range regex system thread tuple
                                # type_traits variant variant2
all = { implies = [全部 27 库] }

[features.algorithm] = { sources=["src/algorithm.cppm"], implies=["core","iterator","range","tuple","type_traits"] }
... (每库一条) ...

[features.thread]               # 编译库: .cppm + 库 TU glob
sources = ["src/thread.cppm", "src/boost_thread_extras.cpp",
           "deps/boost/libs/thread/src/future.cpp",
           "deps/boost/libs/thread/src/win32/*.cpp",
           "deps/boost/libs/thread/src/pthread/once.cpp",
           "deps/boost/libs/thread/src/pthread/thread.cpp"]
flags    = [{ glob = "deps/boost/libs/thread/src/**", defines=["BOOST_THREAD_BUILD_LIB"] }]
implies  = ["chrono","core","io","optional","system","type_traits"]

[target.windows.build]
sources = ["!deps/boost/libs/thread/src/pthread/**"]   # thread 模式: 异平台排除
[target.unix.build]
sources = ["!deps/boost/libs/thread/src/win32/**"]
ldflags = ["-pthread"]
```

要点:
- 每库 feature `sources` = 该库在 base 的源 glob (同字符串, DROP/ADD 以字符串匹配); `implies` = 该库 `.deps` 的模块 import 边。
- 每个库同时列于 base sources 与 feature sources: base 保证库自身可构建且 test 模式全量; feature 声明 gating, build 模式 DROP 剔除未激活库。
- `boost_system_extras.cpp` → feature `system`; `boost_thread_extras.cpp` → feature `thread`。
- thread per-OS TU 互斥: feature 内列全平台 glob, `[target.'cfg'.build]` 用 `!` 排除异平台 (计划 §1.3, spike 已验证)。
- 原 `[build].flags` thread 条目移入 feature `thread.flags` (私有 per-TU, 不传播消费者)。

### 2.2 默认集 18 库闭包

候选 15 + 闭包 3 = 18: `any algorithm chrono core filesystem io iterator json mp11
optional range regex system thread tuple type_traits variant variant2`。

其余 9 库移入 opt-in: `container_hash endian rational scope scope_exit stacktrace
static_string program_options url`。对应测试由 `mcpp test --features <组>` 跑。

## 3. gen_features.py

新脚本, 由 `libs.json` (27 库) + `src/gen_exports/*.deps` (模块 import 边) 生成:

1. 计算每库 feature 的 `implies` (deps) 与 default 闭包;
2. 编译库表 (filesystem/regex/thread/chrono/program_options/stacktrace/json/url) 附库 TU globs;
3. marker splice 写回 `mcpp.toml` 的 `[features]` 块 (`# ── <gen-features> ──` 之间), 幂等;
4. 生成 `scripts/features.lst` (模块库清单, build.mcpp 消费);
5. 输出 thread 的 target `!` 排除表。

> 每库 feature `sources` 与 base `[build].sources` 用**同一 glob 字符串** —
> DROP/ADD 按字符串匹配剔除/加回, 不一致则 gating 失效 (spike 验证)。

## 4. build.mcpp

```cpp
import mcpp;
import std;   // 或 #include <fstream>/<cstdio>
int main() {
    // 读 scripts/features.lst (rerun_if_changed)
    std::string body = "export module boost;\n";
    for (lib : features.lst)
        if (mcpp::has_feature(lib)) body += "export import boost." + lib + ";\n";
    auto out = fs::path(mcpp::out_dir()) / "boost.cppm";
    mtime 稳定写 (内容不变不 touch);
    mcpp::source(out.string());          // 绝对路径
    mcpp::rerun_if_changed("scripts/features.lst");
}
```

语义: `import boost;` 恰好 re-export 激活库。零激活生成空壳。删除静态
`src/boost.cppm`。

## 5. 验证矩阵 (M8 §4)

| 项 | 命令 | 结果 |
|---|---|---|
| 默认 build/test + examples | `mcpp build` / `mcpp test` / `cd examples && mcpp run` | 全绿 |
| 全量 27 库 | `mcpp build --features all` / `mcpp test --features all` | 全绿 |
| 消费者 default-features=false probe | 临时工程 `default-features=false, features=["optional"]` | 绿 |
| opt-in 组测试 | `mcpp test --features container_hash,endian,...` | 绿 |

## 6. 已知取舍与后续

- `[build].sources` 清空会触发 mcpp `src/**` 推断 (toml.cppm L1475), 使 test 模式
  DROP 跳过时全量编译 → 按 feature 分组测试失效; 故保留全量 per-lib glob 于 base,
  仅 feature 声明 gating (§2.1 实测)。
- M9+ 纯头库批量接入时: 每库只需新增 feature 条目 + `.cppm/.inc/.deps`; gen_features.py
  从 libs.json 自动扩展。
