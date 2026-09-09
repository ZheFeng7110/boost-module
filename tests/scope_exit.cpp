// boost.scope_exit smoke — pure include (C1 downgrade, 2026-09-06: the module
// is gone; the library is macro-driven — BOOST_SCOPE_EXIT etc. are the public
// API and macros never cross module boundaries, M10 rule; gcc 16 also
// ODR-conflicts on include+import mixing, see describe.cpp / C1 plan §1.1).
// boost.core has no include counterpart for these names, so its import stays
// (ignore_unused). Version constants now come from boost.version (C5 2026-09-09);
// <boost/version.hpp> is already pulled transitively by <boost/scope_exit.hpp>
// here, so this test does not need to import boost.version — just demonstrate
// that the two faces stay separate.
#include "test_assert.hpp"
#include <boost/scope_exit.hpp>
import boost.core;

int main() {
    int x = 1;
    {
        BOOST_SCOPE_EXIT(&x) {
            x += 10;
        } BOOST_SCOPE_EXIT_END
        ++x;
    }
    assert(x == 12);
    {
        BOOST_SCOPE_EXIT(&x) {
            x += 100;
        } BOOST_SCOPE_EXIT_END
    }
    assert(x == 112);
    boost::ignore_unused(x);
    return 0;
}
