// boost.pool smoke — object pool
#include "test_assert.hpp"
import std;
import boost.pool;

int main() {
    boost::object_pool<int> p;
    int* a = p.construct(42);
    int* b = p.construct(7);
    assert(*a == 42 && *b == 7);
    assert(p.is_from(a));
    p.destroy(a);
    int* c = p.construct(1);
    assert(*c == 1);
    assert(p.get_next_size() > 0);
    boost::pool<> pl(sizeof(int));
    void* mem = pl.malloc();
    assert(mem != nullptr);
    pl.free(mem);
    assert(pl.get_requested_size() == sizeof(int));
    return 0;
}
