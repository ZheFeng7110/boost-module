// boost.geometry smoke — cartesian point distance + area
#include "test_assert.hpp"
import std;
import boost.geometry;

int main() {
    namespace bg = boost::geometry;
    using point_t = bg::model::point<double, 2, bg::cs::cartesian>;
    using poly_t = bg::model::polygon<point_t>;

    point_t a{0.0, 0.0};
    point_t b{3.0, 4.0};
    assert(bg::distance(a, b) == 5.0);

    poly_t poly;
    bg::append(poly.outer(), point_t{0.0, 0.0});
    bg::append(poly.outer(), point_t{4.0, 0.0});
    bg::append(poly.outer(), point_t{4.0, 4.0});
    bg::append(poly.outer(), point_t{0.0, 4.0});
    bg::append(poly.outer(), point_t{0.0, 0.0});
    assert(std::fabs(bg::area(poly)) == 16.0);

    point_t c{1.0, 1.0};
    assert(bg::within(c, poly));
    return 0;
}
