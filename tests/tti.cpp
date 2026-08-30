// boost.tti — include-only smoke (M10 T3: the BOOST_TTI_* macro family
// generates the introspection metafunctions, no module; the import proves
// import+include mixing in one TU)
#include "test_assert.hpp"
import boost.config;
#include <boost/tti/has_member_data.hpp>
#include <boost/tti/has_member_function.hpp>

struct Point {
    int x = 0;
    int y = 0;
    int scaled(int f) { return x * f; }
};

BOOST_TTI_HAS_MEMBER_DATA(x)
BOOST_TTI_HAS_MEMBER_DATA(z)
BOOST_TTI_HAS_MEMBER_FUNCTION(scaled)

static_assert(has_member_data_x<Point, int>::value);
static_assert(!has_member_data_z<Point, int>::value);
// member functions: composite form takes the pointer-to-member type directly
static_assert(has_member_function_scaled<int (Point::*)(int)>::value);

int main() {
    return 0;
}
