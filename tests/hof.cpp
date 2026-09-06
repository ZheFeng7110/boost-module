// boost.hof smoke — C2 re-modularization (2026-09-06): the M9 internal-
// linkage blocker is gone (BOOST_HOF_DECLARE_STATIC_VAR / STATIC_CONSTEXPR
// macros patched to `inline constexpr`, external linkage), so compose/_1 and
// friends export through the boost.hof module face. Macro-heavy consumption
// (BOOST_HOF_STATIC_FUNCTION user-side) stays include-side; mixing include +
// import in one TU ODR-conflicts on gcc 16 (describe.cpp precedent), so the
// import is skipped on gcc — macro and import usage are covered separately
// (this file: module face; the include/macro face lives in
// tests/hof_include.cpp).
#include "test_assert.hpp"
#include <cassert>
#if !defined(__GNUC__) || defined(__clang__)
import boost.hof;
#else
#include <boost/hof.hpp>
#endif

int main() {
    auto c = boost::hof::compose(boost::hof::identity, boost::hof::identity);
    assert(c(5) == 5);
    auto sum = boost::hof::_1 + boost::hof::_2;
    assert(sum(2, 3) == 5);
    assert(boost::hof::always(42)(1, 2) == 42);
    assert(boost::hof::pipable(boost::hof::identity)(7) == 7);
    return 0;
}
