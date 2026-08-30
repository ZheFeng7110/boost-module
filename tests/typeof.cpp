// boost.typeof — include-only smoke (M10 T3: BOOST_AUTO/BOOST_TYPEOF are
// macros, no module; the import proves import+include mixing in one TU)
#include "test_assert.hpp"
import boost.config;
#include <boost/typeof/typeof.hpp>

int main() {
    BOOST_AUTO(v, 1 + 2L);
    assert(v == 3);
    long* p = &v;  // type-level proof: BOOST_AUTO deduced long
    (void)p;
    BOOST_TYPEOF(1 + 2L) w = 4;
    assert(w == 4);
    return 0;
}
