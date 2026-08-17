// boost.bloom smoke — bloom_filter add/probably_contains
#include "test_assert.hpp"
import std;
import boost.bloom;

int main() {
    boost::bloom::filter<int, 64> f(1000, 0.01);
    f.insert(42);
    f.insert(1337);
    assert(f.may_contain(42));
    assert(f.may_contain(1337));
    assert(!f.may_contain(43));
    boost::bloom::filter<int, 64> g = f;
    assert(g.may_contain(42));
    assert(g == f);
    return 0;
}
