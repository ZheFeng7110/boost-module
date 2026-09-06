// boost.units smoke — include/macro face (kept from M9 alongside the C2
// module face in units.cpp: BOOST_UNITS_* macros are include-only, M10 rule —
// this TU exercises the macro-driven consumption pattern a real user would
// write with the vendored headers directly).
#include "test_assert.hpp"
#include <cassert>
#include <boost/units/systems/si.hpp>
#include <boost/units/quantity.hpp>
#include <boost/units/systems/si/io.hpp>

int main() {
    namespace si = boost::units::si;
    namespace u = boost::units;
    u::quantity<si::force> f(6.0 * si::newton);
    u::quantity<si::area> a(2.0 * si::square_meter);
    auto p = f / a;
    assert(u::quantity_cast<double>(p) == 3.0);
    u::quantity<si::pressure> pa = u::quantity<si::pressure>::from_value(3.0);
    assert(u::quantity_cast<double>(pa) == 3.0);
    return 0;
}
