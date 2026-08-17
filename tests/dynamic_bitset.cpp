// boost.dynamic_bitset smoke — dynamic bitset operations
#include "test_assert.hpp"
import std;
import boost.dynamic_bitset;

int main() {
    boost::dynamic_bitset<> b(10, 0);
    assert(b.size() == 10);
    b.set(1);
    b.set(3);
    assert(b.test(1) && b.test(3) && !b.test(2));
    assert(b.count() == 2);
    assert(b.any() && !b.none());
    b.flip(1);
    assert(!b.test(1));
    boost::dynamic_bitset<> c(10);
    c[0] = 1;
    c[5] = 1;
    assert((b & c) == boost::dynamic_bitset<>(10, 0));
    assert((b | c) == (b ^ c) || b[3]);
    assert(b != c);
    b.reset();
    assert(b.none());
    std::string s;
    boost::to_string(b, s);
    assert(s.size() == 10);
    return 0;
}
