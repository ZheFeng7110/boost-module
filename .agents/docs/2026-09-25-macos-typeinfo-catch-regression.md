# macOS-llvm 腿 program_options 测试 SIGABRT 修复 (Mach-O typeinfo 兜底回归)

> 日期: 2026-09-25 · 最后更新: 2026-09-27 · 状态: 第三版修法已实施, 待
> macOS CI 复验 · 分支 `b1.92.0wdev`
> 关联: CI run 35872964147 (macos-llvm group A, Test libraries 失败) ·
> run 36104518727 / 36317554695 (两次修复尝试后仍失败) ·
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
   抛出路径: `typed_value<int>::xparse` → `validators::validate<int>` →
   `boost::throw_exception(invalid_option_value)` →
   `throw wrapexcept<invalid_option_value>` (boost/throw_exception.hpp)。
   这条链上的 `validate<int,char>` / `typed_value<int,char>` 是头文件模板;
   测试 TU 与库侧普通 TU 各发射一份弱符号, first-wins 合并最终选中测试
   (module consumer) TU 的副本 —— 抛出点因此落在消费侧, 而不是 4.2 中
   预设的 extras 普通 TU (本地 build.ninja 链接顺序实证: 测试目标文件
   先于 extras; 详见 4.3)。
2. **M7 先例**: macOS Mach-O 不像 ELF/PE 那样 COMDAT-合并跨模块边界的
   typeinfo, 精确 catch (`po::invalid_option_value`) 在 macOS 落空, 当时以
   `catch (std::exception const&)` 兜底 (单一定义来自 libc++, 被抛对象的
   RTTI 链绕经 std::logic_error 终结于 libc++ 的 std::exception typeinfo,
   指针比较可命中)。
3. **1.92 回归**: 逐字节 diff 1.91/1.92 的 `boost/throw_exception.hpp`、
   `boost/exception/**`、`boost/program_options/errors.hpp` 与测试文件,
   异常层级与抛出代码完全一致 (仅 `detail::arg` 挪命名空间等无关改动)。
   但 1.92 全量重生成模块面 (gen_exports / CMI) 改变了消费 TU 里模板
   实例化的发射形态: 1.91 该实例化仍是可正常展开的普通代码 (run
   35872234898 绿), 1.92 则连 RTTI 无关的 `catch(...)` 都够不到 (异常
   未走到展开路径即 terminate) —— 属编译器/运行时在 macOS 模块消费 TU
   上的展开路径回归, 无法在本仓库内根治。附带现象: 精确 catch 的
   typeinfo 命中本就是 M7 已知的跨边界问题 (1.91 靠
   `catch (std::exception const&)` 兜底)。
4. **定性**: 两个问题叠加 —— M7 的 "macOS Mach-O typeinfo 跨模块边界不
   合并" (catch 匹配不可靠), 加上 1.92 消费 TU 展开路径失效 (catch(...)
   都兜不住)。根治需动 mcpp/clang 模块发射策略 (超出本仓库范围, M7 同一
   决策); 仓库内可行的确定性修法是把抛出点从消费 TU 挪回普通 TU 并钉死
   (4.3)。

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

### 4.2 第二次尝试 (ab0e5301, 未奏效): throw+catch 移入库侧普通 TU

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

但 CI run 36317554695 (ab0e5301) 仍以同一条消息 SIGABRT —— 函数体搬家
不够, 见 4.3。

### 4.3 第三次尝试 (最终): 显式实例化 + extern template 钉死抛出点

**根因补完**: `validate<int,char>` / `typed_value<int,char>` 是头文件
模板, 测试 TU (module consumer) 与库内普通 TU 各自发射一份弱符号
(`W`/`V`, vague linkage)。ELF/Mach-O 对弱定义都是 first-wins 合并, 而
链接行里测试目标文件在 extras 之前 (本地 build.ninja 实证:
`obj/program_options.o` 先于 `obj/boost_program_options_extras.o`), 故
**合并胜出的仍是消费 TU 的实例化** —— `store()`/`value_semantic_codecvt_helper::parse`
的虚调最终落到消费 TU 的 `xparse`/`validate<int,char>`, 抛出点在模块
消费侧, 4.2 的 landing pad (extras 内) 永远等不到这个异常。b1.92 里
消费侧实例化的展开在 macOS 失效 (b1.91 的同一份代码还正常), 属编译器/
运行时的模块侧回归, 本仓库无法根治; 能做的是让抛出点不再落在消费侧。

**修法** (与 thread/leaf 的 clone_impl 先例 M7c/M9 同一机制):

- `src/boost_program_options_extras.cpp`: 对本路径两条模板
  (`typed_value<int,char>` class + `validate<int,char>` function) **显式
  实例化**, 生成库侧唯一定义;
- 生成面 `src/gen_exports/program_options.inc` (经
  `scripts/patchs/program_options.patch` 幂等重放) 加
  `extern template class typed_value<int, char>;` 与
  `extern template void validate<int, char>(...);`, 抑制消费 TU 的隐式
  实例化 —— 消费侧只剩 `value<int>()` 的调用与重定位, 抛出点被钉死在本
  普通 TU (与 tests/exception.cpp 同形态)。

本地验证: 测试目标文件中 `validate<int,char>`/`typed_value<int,char>`
由 `W` 定义退化为 `U` 引用 (gcc 16.1.0 与 clang 22.1.8 两侧一致),
全程序唯一库侧定义; `mcpp test program_options --features program_options`
在 gcc 16.1.0 与 llvm 22.1.8 两套工具链下均 1/1 通过。

### 4.4 修改文件

- `src/boost_program_options_extras.cpp` (显式实例化 + 注释)
- `scripts/patchs/program_options.patch` (extern template, 生成面重放)
- `tests/program_options.cpp` (注释同步; 断言不变)
- `scripts/gen_features.py` (EXTRAS 注释同步)

## 5. 验证

- 符号面: gcc 16.1.0 / clang 22.1.8 下, 测试 TU 都不再发射
  `typed_value<int,char>` vtable/xparse 与 `validate<int,char>` (退化为
  `U` 引用), 全程序唯一库侧定义落在 extras 普通 TU。
- `mcpp test program_options --features program_options` 两套工具链均
  1/1 通过; exception / throw_exception / any / lexical_cast 相邻用例
  回归通过。
- macOS-llvm 腿待 CI 复跑确认 (本修复提交后由 Tests workflow 验证)。
