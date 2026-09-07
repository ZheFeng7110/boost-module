// boost.hof smoke — C2 re-modularization (2026-09-06): the M9 internal-
// linkage blocker is gone (BOOST_HOF_DECLARE_STATIC_VAR / STATIC_CONSTEXPR
// macros patched to `inline constexpr`, external linkage), so compose/_1 and
// friends export through the boost.hof module face. The module import works
// on all three compilers — CI (gcc 16.1 linux leg, 2026-09) verified that
// importing boost.hof does NOT trip the gcc include+import ODR conflict
// (describe.cpp precedent does not apply here: hof's GMF carries no
// make_void/mp_list-style collision family) — so no __GNUC__ guard is
// needed. Macro-heavy consumption (BOOST_HOF_STATIC_FUNCTION user-side)
// stays include-side and is covered in tests/hof_include.cpp.
#include "test_assert.hpp"
#include <cassert>
import boost.hof;

int main() {
    auto c = boost::hof::compose(boost::hof::identity, boost::hof::identity);
    assert(c(5) == 5);
    auto sum = boost::hof::_1 + boost::hof::_2;
    assert(sum(2, 3) == 5);
    assert(boost::hof::always(42)(1, 2) == 42);
    assert(boost::hof::pipable(boost::hof::identity)(7) == 7);
    return 0;
}
