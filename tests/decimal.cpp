// boost.decimal smoke — decimal floating point types
#include "test_assert.hpp"
import std;
import boost.decimal;

int main() {
    boost::decimal::decimal32_t a(1.5);
    boost::decimal::decimal32_t b(2.5);
    boost::decimal::decimal32_t c = a + b;
    assert(c == boost::decimal::decimal32_t(4.0));
    assert(b > a);
    assert(boost::decimal::decimal32_t(0) != boost::decimal::decimal32_t(1));
    boost::decimal::decimal64_t d(3);
    assert(d + boost::decimal::decimal64_t(0.5) == boost::decimal::decimal64_t(3.5));
    assert(boost::decimal::abs(boost::decimal::decimal32_t(-7)) == boost::decimal::decimal32_t(7));
    assert(boost::decimal::isnan(boost::decimal::decimal32_t(1.0)) == false);
    return 0;
}
