// boost.describe smoke — pure include (C1 downgrade, 2026-09-06: the module
// is gone; the public API is the BOOST_DESCRIBE_* macro family, which can
// never cross a module boundary — M10 rule — and gcc 16 ODR-conflicts on
// include+import mixing in one TU, see the C1 plan §1.1). Same consumer rule
// as the T3 macro libraries (mirror of tests/exception.cpp).
#include "test_assert.hpp"
#include <cassert>
#include <string>
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
