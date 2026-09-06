// boost.hof smoke — include/macro face (kept from M9 alongside the C2 module
// face in hof.cpp: BOOST_HOF_STATIC_FUNCTION / STATIC_LAMBDA are macro APIs,
// macros never cross a module boundary, M10 rule — a user TU declaring its
// own static function objects consumes the headers directly).
#include "test_assert.hpp"
#include <cassert>
#include <boost/hof.hpp>

BOOST_HOF_STATIC_FUNCTION(add1) = [](int x) { return x + 1; };

int main() {
    auto c = boost::hof::compose(add1, boost::hof::always(3));
    assert(c(5) == 4);
    auto sum = boost::hof::_1 + boost::hof::_2;
    assert(sum(2, 3) == 5);
    assert(boost::hof::identity(7) == 7);
    // reverse_fold: right-to-left fold (f(3,2) then f(1, that) → 132)
    assert(boost::hof::reverse_fold([](int x, int y) { return x * 10 + y; })(
               1, 2, 3) == 132);
    return 0;
}
