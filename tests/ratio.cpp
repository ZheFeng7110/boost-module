// boost.ratio smoke — compile-time rational arithmetic
#include "test_assert.hpp"
import std;
import boost.ratio;

int main() {
    using r1 = boost::ratio<1, 2>;
    using r2 = boost::ratio<1, 3>;
    using sum = boost::ratio_add<r1, r2>;
    static_assert(sum::num == 5 && sum::den == 6);
    using diff = boost::ratio_subtract<r1, r2>;
    static_assert(diff::num == 1 && diff::den == 6);
    using prod = boost::ratio_multiply<r1, r2>;
    static_assert(prod::num == 1 && prod::den == 6);
    using quot = boost::ratio_divide<r1, r2>;
    static_assert(quot::num == 3 && quot::den == 2);
    static_assert(boost::ratio_equal<boost::ratio<2, 4>, r1>::value);
    static_assert(boost::ratio_less<r2, r1>::value);
    using m = boost::milli;
    static_assert(m::num == 1 && m::den == 1000);
    return 0;
}
