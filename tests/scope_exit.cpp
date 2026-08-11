// boost.scope_exit smoke — the library is macro-driven (BOOST_SCOPE_EXIT etc.),
// macros cannot cross module boundaries, so this test exercises the sanctioned
// hybrid mode: #include the macro header + import the module (M0 §5, M3 bypass
// pattern — macros.hpp covers version macros; scope_exit's own macros are used
// directly here as they are the library's public API).
#include "test_assert.hpp"
#include <boost/scope_exit.hpp>
import boost.scope_exit;
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
    boost::ignore_unused(boost::BOOST_VERSION);
    return 0;
}
