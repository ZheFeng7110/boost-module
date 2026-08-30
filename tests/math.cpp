// boost.math smoke — header-only module face (src/tr1 excluded, M11 doc §2)
#include "test_assert.hpp"
import std;
import boost.math;

int main() {
    double g = boost::math::tgamma(5.0);  // Γ(5) = 4! = 24
    assert(g > 23.999 && g < 24.001);

    double pi = boost::math::constants::pi<double>();
    assert(pi > 3.14159 && pi < 3.14160);

    boost::math::students_t dist(5.0);
    double p = boost::math::pdf(dist, 1.0);
    assert(p > 0.0 && p < 1.0);

    assert(boost::math::isfinite(pi));
    return 0;
}
