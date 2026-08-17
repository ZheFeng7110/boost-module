// boost.compat smoke — std backports (span, bind_front, function_ref)
#include "test_assert.hpp"
import std;
import boost.compat;

int main() {
    auto add = [](int a, int b) { return a + b; };
    auto plus2 = boost::compat::bind_front(add, 2);
    assert(plus2(5) == 7);
    assert(plus2(10) == 12);
    boost::compat::function_ref<int(int)> fr = [](int x) { return x * 3; };
    assert(fr(4) == 12);
    static_assert(std::is_same<boost::compat::decay_t<const int&>, int>::value);
    static_assert(std::is_same<boost::compat::add_const_t<int>, const int>::value);
    return 0;
}
