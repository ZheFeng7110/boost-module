// boost.cobalt smoke — compiled lib linkage (channel/detail/io TUs, asio-based).
// <coroutine> is included before the import so std::coroutine_traits is
// findable for the consumer-defined coroutine; run() and task<> are exported
// by the module.
#include "test_assert.hpp"
#include <coroutine>
import boost.cobalt;

boost::cobalt::task<int> answer() { co_return 42; }

int main() {
    assert(boost::cobalt::run(answer()) == 42);
    return 0;
}
