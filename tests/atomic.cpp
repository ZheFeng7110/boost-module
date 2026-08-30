// boost.atomic smoke — compiled lib linkage (lock_pool / find_address TUs)
#include "test_assert.hpp"
import std;
import boost.atomic;

int main() {
    boost::atomic<int> a(0);
    a.fetch_add(5, boost::memory_order_relaxed);
    assert(a.load() == 5);
    int prev = a.exchange(3);
    assert(prev == 5);
    int expected = 3;
    bool ok = a.compare_exchange_strong(expected, 7);
    assert(ok && a.load() == 7);

    boost::atomic_flag f;
    assert(!f.test_and_set());
    f.clear();

    boost::atomic<bool> b(true);
    assert(b.load());
    assert(boost::atomic<int>(42).load() == 42);
    return 0;
}
