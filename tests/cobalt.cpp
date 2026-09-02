// boost.cobalt smoke — compiled lib linkage (channel/detail/io TUs, asio-based).
// <coroutine> is included before the import so std::coroutine_traits is
// findable for the consumer-defined coroutine; run() and task<> are exported
// by the module.
#include "test_assert.hpp"
#include <coroutine>
// gcc 16.1 module instantiation context: the std::_Sp_counted_ptr_inplace /
// __is_nothrow_new_constructible_impl bodies instantiated from the
// boost.cobalt CMI use typeid / placement-new, whose declarations live in
// <typeinfo> / <new> — the consumer TU must pull them in itself.
#include <new>
#include <typeinfo>
import boost.cobalt;

boost::cobalt::task<int> answer() { co_return 42; }

int main() {
    assert(boost::cobalt::run(answer()) == 42);
    return 0;
}
