// boost-module/macros.hpp — 旁路头 (M3)
//
// C++23 named modules 不能导出宏。需要**宏拼写**的消费者 (例如预处理器条件
// `#if BOOST_VERSION >= 109100`, 或传递给第三方宏体系) 在 `import boost.*;`
// 之前 include 本头。
//
//   例:
//     #include <boost-module/macros.hpp>
//     import boost.core;
//     #if BOOST_VERSION >= 109100
//     ...
//
// 模块化拼写见 boost.core 的 re-homing: import 后可用 boost::BOOST_VERSION
// (constexpr int)。同一 TU 内两种拼写互斥 — 宏会展开并吞掉 boost::BOOST_VERSION
// 中的同名 token (→ boost::109100), 二选一。
//
// 约束 (M0 §5): 本头引入的内容与模块 GMF include 集不相交, 仅承载宏定义
// (version.hpp 只定义宏, 无外部链接实体, 不产生 ODR/模块冲突)。
// 扩展策略: 后续里程碑按需追加 (如 BOOST_SCOPED_ENUM 等), 追加前核对
// 与各模块 GMF include 集的关系。
#ifndef BOOST_MODULE_MACROS_HPP
#define BOOST_MODULE_MACROS_HPP

#include <boost/version.hpp>

#endif // BOOST_MODULE_MACROS_HPP
