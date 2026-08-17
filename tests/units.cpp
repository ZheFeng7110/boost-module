// boost.units — include-only smoke (M9: SI unit constants are internal-linkage
// static constexpr objects, not module-exportable; consumers #include the
// header — import+include mixing is standard-compliant)
#include "test_assert.hpp"
#include <cassert>
#include <boost/units/systems/si.hpp>
#include <boost/units/quantity.hpp>

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
