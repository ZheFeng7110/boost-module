// boost.describe smoke — describe members/enumerators via the module API
// (BOOST_DESCRIBE_STRUCT is a macro: include-only, per the M3 macro policy —
// mixing include + import in one TU is standard-compliant)
#include "test_assert.hpp"
#include <cassert>
#include <string>
#include <type_traits>
import boost.describe;
#include <boost/describe.hpp>

struct Point {
    int x = 0;
    int y = 0;
};
BOOST_DESCRIBE_STRUCT(Point, (), (x, y))

enum class Color { Red, Green, Blue };
BOOST_DESCRIBE_ENUM(Color, Red, Green, Blue)

int main() {
    auto members = boost::describe::describe_members<Point,
        boost::describe::mod_public | boost::describe::mod_inherited>();
    auto enums = boost::describe::describe_enumerators<Color>();
    assert(std::string(boost::describe::enum_to_string(Color::Green, "?")) ==
           "Green");
    Color c = Color::Red;
    assert(boost::describe::enum_from_string("Blue", c));
    assert(c == Color::Blue);
    Point p{1, 2};
    (void)p;
    (void)members;
    return 0;
}
