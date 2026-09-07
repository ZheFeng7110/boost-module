// boost.units smoke — C2 re-modularization (2026-09-06): the M9 internal-
// linkage blocker is gone (BOOST_UNITS_STATIC_CONSTANT patched to
// `inline constexpr`), so the SI unit constants (si::meter etc.) export
// through the boost.units module face alongside the quantity/class surface.
// The module import works on all three compilers — CI (gcc 16.1 linux leg,
// 2026-09) verified that importing boost.units does NOT trip the gcc
// include+import ODR conflict (describe.cpp precedent does not apply: the
// units GMF carries no collision-prone entity family, despite the large
// macro face M10 own-283 — macros and the module face coexist fine). The
// BOOST_UNITS_* macro API stays include-side and is covered in
// tests/units_include.cpp.
#include "test_assert.hpp"
#include <cassert>
import boost.units;

int main() {
    namespace si = boost::units::si;
    namespace u = boost::units;
    u::quantity<si::length> d(2.0 * si::meter);
    u::quantity<si::time> t(4.0 * si::second);
    auto v = d / t;
    assert(u::quantity_cast<double>(v) == 0.5);
    u::quantity<si::length> d2 = d + 3.0 * si::meter;
    assert(u::quantity_cast<double>(d2) == 5.0);
    assert(u::quantity<si::frequency>(1.0 / si::second) ==
           u::quantity<si::frequency>(1.0 * si::hertz));
    return 0;
}
