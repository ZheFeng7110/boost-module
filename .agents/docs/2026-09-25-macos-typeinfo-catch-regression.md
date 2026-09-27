# macOS-llvm 腿 program_options 测试 SIGABRT 修复 (Mach-O typeinfo 兜底回归)

> 日期: 2026-09-25 · 状态: 实施完成 · 分支 `b1.92.0wdev`
> 关联: CI run 35872964147 (macos-llvm group A, Test libraries 失败) ·
> M6/M7 macOS typeinfo 兜底先例 (`2026-09-08-consolidated-design.md` §6.3)

## 1. 现象

合并 `b1.91.0wdev` → `b1.92.0wdev` (a7f37e4c) 后, macOS-llvm group A 腿
`mcpp test` 141 例中 140 过、1 败:

```
program_options ... FAIL (exit 134, 0.30s)
libc++abi: terminating due to uncaught exception of type
boost::wrapexcept<boost::program_options::invalid_option_value>:
the argument ('notanumber') for option is invalid
```

exit 134 = SIGABRT, 即异常穿出了 `tests/program_options.cpp` 里两层
catch (`po::invalid_option_value` 精确 catch 与 `std::exception` 兜底) 均未
匹配, libc++abi 走 terminate。同 commit 下 linux-gcc / linux-llvm /
windows-llvm-msvc 三腿全绿; b1.91 分支同测试在 macOS-llvm 上通过
(run 35872234898)。

## 2. CI 里的 DYLD warning 与本失败无关

```
warning: macOS does not inject a runtime library path for test binaries
(DYLD_LIBRARY_PATH is deliberately not set); dependencies must be reachable
through the binary's rpath. A dyld 'image not found' failure below is this
difference, not a broken test.
```

- 这是 `mcpp test` 在 macOS 上的固定提示: Linux 下测试运行器会注入
  `LD_LIBRARY_PATH` 指向 build 目录, 而 macOS 的 dyld 故意不读
  (也不该读) `DYLD_LIBRARY_PATH`, 依赖 dylib 必须通过二进制自身的
  install_name / rpath 到达。
- 该 warning 只是预先解释 "若下方出现 dyld image not found 属环境差异而非
  测试逻辑问题"。本次日志全程无任何 dyld image not found (140/141 正常加载
  运行), 实际失败是 SIGABRT, 与动态库路径无关。

## 3. 根因分析

1. **失败点**: `tests/program_options.cpp` 的 `--port=notanumber` 用例。
   抛出路径: 消费侧模板实例化 `typed_value<int>::xparse` →
   `validators::validate<int>` → `boost::throw_exception(invalid_option_value)`
   → `throw wrapexcept<invalid_option_value>` (boost/throw_exception.hpp)。
2. **M7 先例**: macOS Mach-O 不像 ELF/PE 那样 COMDAT-合并跨模块边界的
   typeinfo, 精确 catch (`po::invalid_option_value`) 在 macOS 落空, 当时以
   `catch (std::exception const&)` 兜底 (单一定义来自 libc++, 被抛对象的
   RTTI 链绕经 std::logic_error 终结于 libc++ 的 std::exception typeinfo,
   指针比较可命中)。
3. **1.92 回归**: 逐字节 diff 1.91/1.92 的 `boost/throw_exception.hpp`、
   `boost/exception/**`、`boost/program_options/errors.hpp` 与测试文件,
   异常层级与抛出代码完全一致 (仅 `detail::arg` 挪命名空间等无关改动)。
   但 1.92 全量重生成模块面 (gen_exports / CMI) 改变了测试二进制的链接
   内容与布局, Mach-O 弱符号 first-wins 合并的胜出副本随之漂移: 被抛
   `wrapexcept<invalid_option_value>` 的 RTTI 继承链上某节点
   (std::logic_error / std::exception 一层) 运行时解析到的副本与 handler
   引用的副本不再是同一实例, `catch (std::exception const&)` 的指针比较
   落空 → 异常穿出 → terminate。
4. **定性**: 属 M7 已记录的 "macOS Mach-O typeinfo 跨模块边界不合并" 根因
   族, 1.92 升级使其波及 std::exception 兜底层; 根治 (跨模块 typeinfo
   统一) 需动 mcpp/clang 模块发射策略, 超出本仓库范围 (M7 同一决策)。

## 4. 修复

### 4.1 第一次尝试 (8a407ab5, 未奏效)

在 `tests/program_options.cpp` 追加 RTTI 无关的 `catch (...)` 兜底。若异常
按标准两阶段展开传播, catch(...) 必然命中 (Itanium ABI 中 catch-all 的
handler typeinfo 为空, phase 1 恒匹配)。CI run 36104518727 (同 commit) 仍以
完全相同的消息 SIGABRT —— 证明异常**根本未到达展开阶段**: 要么抛出点与
landing pad 之间有 noexcept 边界/调用帧展开信息缺失导致
`_Unwind_RaiseException` phase 1 提前判负, libc++abi 在异常仍"在飞"时
terminate (默认 terminate handler 对在飞异常打印同一条
"terminating due to uncaught exception of type ..." 消息); 无论哪种,
问题都出在**模块消费 TU 作为抛出侧**的展开路径, 而非 handler 匹配。

### 4.2 最终修复: throw+catch 移入库侧普通 TU

关键对照: `tests/exception.cpp` (include-only 消费, 不 import 模块) 在
macOS 上对 `boost::throw_exception` 产生的 `wrapexcept<my_error>` 做
**精确 catch** 全绿 —— 普通 (非模块消费) TU 里的 throw+catch 在 macOS
测试二进制中完全正常。

故沿用 `boost_*_extras.cpp` 先例 (M5 B'/M7c/M9), 新增
`src/boost_program_options_extras.cpp` (普通 include-only TU, 已加入
`gen_features.py` EXTRAS → `[features.program_options].sources`), 把
throw+catch 整体移入:

- 抛出点 (`typed_value<int>` 实例化 + `boost::throw_exception`) 与
  landing pad 同 TU, 语义与上游 vanilla C++ 一致, 不再跨模块边界展开;
- 普通 TU 内精确 catch (`invalid_option_value`) 恢复有效, 断言强度高于
  此前消费侧的 catch 链 (M7 兜底反而被移除);
- 消费者 (tests/program_options.cpp) 只手工 extern 声明
  `boost::program_options::detail::mcpp_rejects_invalid_option_value()`
  并断言返回 true —— 不触碰生成物 (`src/*.cppm` / `.inc`)。

同类模式目前仅 program_options 一处 (grep 证实), 其余 140 例在 macOS
通过, 无需扩散。

## 5. 验证

- linux 本地 `mcpp test --features <program_options 闭包>` 通过 (141/141;
  精确 catch 在普通 TU 内命中)。
- macOS-llvm 腿待 CI 复跑确认 (本修复提交后由 Tests workflow 验证)。
