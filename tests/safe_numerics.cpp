// boost.safe_numerics smoke — checked integer arithmetic
#include "test_assert.hpp"
import std;
import boost.safe_numerics;

int main() {
    boost::safe_numerics::safe<int> a(10);
    boost::safe_numerics::safe<int> b(20);
    auto c = a + b;
    assert(c == 30);
    auto d = b - a;
    assert(d == 10);
    auto e = a * b;
    assert(e == 200);
    auto f = b / a;
    assert(f == 2);
    assert(a < b && b > a);
    bool caught = false;
    try {
        boost::safe_numerics::safe<int> big(2000000000);
        boost::safe_numerics::safe<int> big2(2000000000);
        auto overflow = big + big2;
        (void)overflow;
    } catch (std::system_error const&) {
        caught = true;
    }
    assert(caught);
    return 0;
}
