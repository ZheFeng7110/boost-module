// boost.polygon smoke — point/interval/rectangle data types + accessors
#include "test_assert.hpp"
import std;
import boost.polygon;

int main() {
    namespace gp = boost::polygon;

    gp::point_data<int> p(3, 4);
    assert(gp::x(p) == 3);
    assert(gp::y(p) == 4);

    gp::interval_data<int> iv(1, 5);
    assert(iv.low() == 1 && iv.high() == 5);

    gp::rectangle_data<int> rect(0, 0, 10, 20);
    assert(gp::xl(rect) == 0 && gp::xh(rect) == 10);
    assert(gp::yl(rect) == 0 && gp::yh(rect) == 20);
    assert(gp::delta(rect, gp::HORIZONTAL) == 10);
    assert(gp::area(rect) == 200);

    gp::point_data<int> a(1, 1);
    gp::point_data<int> b(15, 25);
    assert(gp::contains(rect, a, true));
    assert(!gp::contains(rect, b, true));
    return 0;
}
