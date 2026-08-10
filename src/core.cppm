// M3 final form (derived from the scripts/gen_exports.py draft; hand-finalized)
module;
#include <boost/core/alloc_construct.hpp>
#include <boost/core/allocator_traits.hpp>
#include <boost/core/bit.hpp>
#include <boost/core/checked_delete.hpp>
#include <boost/core/cmath.hpp>
#include <boost/core/default_allocator.hpp>
#include <boost/core/empty_value.hpp>
#include <boost/core/exchange.hpp>
#include <boost/core/explicit_operator_bool.hpp>
#include <boost/core/fclose_deleter.hpp>
#include <boost/core/first_scalar.hpp>
#include <boost/core/functor.hpp>
#include <boost/core/identity.hpp>
#include <boost/core/ignore_unused.hpp>
#include <boost/core/is_same.hpp>
#include <boost/core/launder.hpp>
#include <boost/core/lightweight_test_trait.hpp>
#include <boost/core/make_span.hpp>
#include <boost/core/memory_resource.hpp>
#include <boost/core/no_exceptions_support.hpp>
#include <boost/core/noncopyable.hpp>
#include <boost/core/null_deleter.hpp>
#include <boost/core/pointer_in_range.hpp>
#include <boost/core/quick_exit.hpp>
#include <boost/core/ref.hpp>
#include <boost/core/scoped_enum.hpp>
#include <boost/core/serialization.hpp>
#include <boost/core/size.hpp>
#include <boost/core/snprintf.hpp>
#include <boost/core/swap.hpp>
#include <boost/core/typeinfo.hpp>
#include <boost/core/uncaught_exceptions.hpp>
#include <boost/core/underlying_type.hpp>
#include <boost/core/use_default.hpp>
#include <boost/core/verbose_terminate_handler.hpp>
#include <boost/core/yield_primitives.hpp>

export module boost.core;

// 对象宏 re-homing (M3): 宏无法跨模块导出。上游 <boost/version.hpp> 的对象宏
// 以 boost:: 命名空间 constexpr 重置于此 (拼写保持): 消费者 import 后可用
// boost::BOOST_VERSION。值须与 deps/boost/boost/version.hpp 一致 — tests/macros.cpp
// 在旁路头 (include/boost-module/macros.hpp) 参与下交叉校验。
// 注意: 同一 TU 中若定义了同名宏 (include <boost-module/macros.hpp>), 宏展开会
// 吞掉 boost::BOOST_VERSION 拼写 (→ boost::109100), 两种拼写互斥, 二选一。
export namespace boost {
  constexpr int BOOST_VERSION = 109100;
  constexpr const char* BOOST_LIB_VERSION = "1_91";
}

#include "gen_exports/core.inc"

