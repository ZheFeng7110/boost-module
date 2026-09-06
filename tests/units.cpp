// boost.units smoke — C2 re-modularization (2026-09-06): the M9 internal-
// linkage blocker is gone (BOOST_UNITS_STATIC_CONSTANT patched to
// `inline constexpr`), so the SI unit constants (si::meter etc.) export
// through the boost.units module face alongside the quantity/class surface.
// The BOOST_UNITS_* macro API stays include-side; mixing include + import in
// one TU ODR-conflicts on gcc 16 (describe.cpp precedent; units' macro face
// is large, M10 own-283) — so this TU imports only (gcc falls back to pure
// include), and the macro face is covered in tests/units_include.cpp.
#include "test_assert.hpp"
#include <cassert>
#if !defined(__GNUC__) || defined(__clang__)
import boost.units;
#else
#include <boost/units/systems/si.hpp>
#include <boost/units/quantity.hpp>
#endif

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
