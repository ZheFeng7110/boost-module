// boost.histogram smoke — 1D/2D histograms
#include "test_assert.hpp"
import std;
import boost.histogram;

int main() {
    namespace bh = boost::histogram;
    auto h = bh::make_histogram(bh::axis::regular<>(4, 0.0, 4.0));
    h(0.5);
    h(1.5);
    h(1.5);
    h(3.5);
    assert(h.axis(0).size() == 4);
    assert(h.at(0) == 1);
    assert(h.at(1) == 2);
    assert(h.at(3) == 1);
    assert(h.axis(0).size() == 4);
    auto h2 = bh::make_histogram(bh::axis::integer<>(0, 3), bh::axis::integer<>(0, 2));
    h2(1, 1);
    h2(2, 0);
    assert(h2.at(1, 1) == 1 && h2.at(2, 0) == 1);
    return 0;
}
