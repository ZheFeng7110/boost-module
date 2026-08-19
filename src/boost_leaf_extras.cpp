// boost-module (M9): boost::leaf exception explicit instantiation.
//
// 背景: 与 boost.thread 的 clone_impl (M7c) 同一 gcc 16.1.0 modules 管线问题 —
// 消费者 TU 会为 leaf::detail::exception<T> (多重继承 exception_base/error_id)
// 发射部分 vtable, 但其 non-virtual thunk (get_error_id/get_type_name 的
// 二级 vtable 槽) 在模块消费者 TU 中不发射 → undefined reference (linux-gcc
// 与 mingw-gcc 均复现)。
//
// 修法 (与 boost_thread_extras.cpp 同模式): 在普通编译单元显式实例化消费者
// 会触达的特化, 使完整 vtable + thunk 单份存在于库 TU; leaf.inc 中的
// extern template 声明抑制消费者侧的隐式实例化。
//
//   exception<bad_result> — result<T> 的 .value() 失败路径 (result.hpp
//   throw_exception(get_error_id(), bad_result{}))

#include <boost/leaf/result.hpp>

template class boost::leaf::detail::exception<boost::leaf::bad_result>;
