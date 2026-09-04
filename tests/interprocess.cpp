// boost.interprocess smoke — managed heap memory (no OS objects)
#include "test_assert.hpp"
import std;
import boost.interprocess;

int main() {
    namespace ip = boost::interprocess;
    ip::managed_heap_memory mem(4096);

    auto& named = *static_cast<int*>(mem.allocate_aligned(sizeof(int), alignof(int)));
    named = 42;
    assert(named == 42);
    mem.deallocate(&named);

    ip::managed_heap_memory mem2(1024);
    {
        auto guard = mem2.allocate(128);
        assert(guard != nullptr);
    }
    return 0;
}
