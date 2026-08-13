// boost-module (M7): boost.exception clone_impl explicit instantiations.
//
// 背景: gcc 16.1.0 的 C++20 modules 管线中, 消费者 TU 会引用
// clone_impl<T> 的 vtable + virtual thunk (clone_impl 虚继承 clone_base),
// 但 gcc 在模块消费者 TU 不发射这些 thunk → undefined reference。
// (clang/msvc 无此问题; Windows 与 linux-llvm 均过, linux-gcc/mingw 挂)
//
// 修法 (与 boost_system_extras.cpp 同模式): 在普通编译单元显式实例化
// boost.thread 异常路径会触达的三个特化, 使 vtable/thunk 单份存在于
// 库 TU (libboost)。消费者不再需要自行发射。
//
//   clone_impl<broken_promise>               — boost::future/promise 断链
//   clone_impl<unknown_exception>            — current_exception() 兜底
//   clone_impl<std_exception_ptr_wrapper>    — wrap_exception_ptr / exception_ptr
//
// 注意: 显式实例化强制实例化含私有成员在内的所有成员 (不受访问控制影响),
// 生成完整 vtable + 全部 thunk。

#include <boost/exception/exception.hpp>
#include <boost/exception_ptr.hpp>
#include <boost/thread/future.hpp>

template class boost::exception_detail::clone_impl<boost::broken_promise>;
template class boost::exception_detail::clone_impl<boost::unknown_exception>;
template class boost::exception_detail::clone_impl<boost::exception_detail::std_exception_ptr_wrapper>;
