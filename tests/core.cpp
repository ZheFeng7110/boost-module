// boost.core smoke — exchange, ignore_unused, core::swap
// (BOOST_VERSION / BOOST_LIB_VERSION moved to boost.version module — C5 2026-09-09;
//  see tests/version.cpp for those constants.)
#include "test_assert.hpp"
import std;
import boost.core;

int main() {
    int x = 1;
    int old = boost::exchange(x, 2);
    assert(old == 1 && x == 2);
    boost::ignore_unused(old, x);
    int a = 5, b = 9;
    boost::swap(a, b);
    assert(a == 9 && b == 5);
    boost::swap(a, b);
    assert(a == 5 && b == 9);
    boost::empty_value<int> ev(boost::empty_init, 7);
    assert(ev.get() == 7);
    return 0;
}
