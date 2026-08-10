// macros bypass header + module re-homing — two consumer paths for version info:
// 1. macros.hpp provides the macro spelling (preprocessor usage)
// 2. import boost.core; provides boost::BOOST_VERSION (module spelling)
// NOTE: the two spellings are mutually exclusive in one TU — a defined macro
// would expand away boost::BOOST_VERSION (→ boost::109100), so this TU uses
// the macro form and core.cpp checks the module form.
#include <boost-module/macros.hpp>
import boost.core;

#if !defined(BOOST_VERSION)
#error macros.hpp must define BOOST_VERSION
#endif
#if BOOST_VERSION != 109100
#error BOOST_VERSION must be 109100 for Boost 1.91.0
#endif
#if BOOST_VERSION / 100000 != 1 || BOOST_VERSION / 100 % 1000 != 91
#error BOOST_VERSION must encode 1.91
#endif

static_assert(BOOST_LIB_VERSION[0] == '1');

int main() {
    return 0;
}
