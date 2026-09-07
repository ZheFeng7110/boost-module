// boost.lambda2 smoke — C4 re-modularization (2026-09-07): _1.._9/first/
// second are `inline constexpr` objects and the operator surface is function
// templates — external linkage throughout, no vendored patch needed. The M10
// include-only verdict came from the own-family macro-percentage screen
// (9/9 macros "own"), but every BOOST_LAMBDA2_* macro is an implementation
// X-macro #undef'd at the end of the header; none is user-facing.
#include "test_assert.hpp"
#include <cassert>
#include <map>
#include <string>
import boost.lambda2;

int main() {
    using namespace boost::lambda2;
    auto inc = 1 + _1;
    assert(inc(41) == 42);
    auto sum = _1 + _2;
    assert(sum(2, 3) == 5);
    auto cmp = _1 < _2;
    assert(cmp(1, 2));
    std::map<int, std::string> m{{1, "one"}};
    auto lookup = _1[ _2 ];
    assert(lookup(m, 1) == "one");
    assert(first(std::make_pair(7, 8)) == 7);
    assert(second(std::make_pair(7, 8)) == 8);
    return 0;
}
