// boost.version smoke (C5 2026-09-09, replaces tests/macros.cpp which
// validated the now-deleted include/boost-module/macros.hpp bypass header).
//
// Validates:
//   - `import boost.version;` provides `boost::BOOST_VERSION` and
//     `boost::BOOST_LIB_VERSION` constants at the values seeded from the
//     vendored <boost/version.hpp> (109100 / "1_91" for Boost 1.91.0).
//   - the values match the encoded major/minor (1.91).
//
// The LIBS_SPECIAL design (boost_common.py: `boost.version` has a .cppm,
// no TU globs, no .deps file, hand-written TU) means there is no
// gen_exports.py `.inc` for this lib — `tests/version.cpp` is the
// dedicated smoke for it.
#include "test_assert.hpp"
import boost.version;

int main() {
    static_assert(boost::BOOST_VERSION == 109100);
    static_assert(boost::BOOST_LIB_VERSION[0] == '1');
    assert(boost::BOOST_VERSION / 100000 == 1);
    assert(boost::BOOST_VERSION / 100 % 1000 == 91);
    return 0;
}
