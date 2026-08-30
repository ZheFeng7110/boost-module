// boost.random smoke — compiled lib linkage (random_device TU)
#include "test_assert.hpp"
import std;
import boost.random;

int main() {
    boost::random::random_device rd;   // random_device.cpp TU symbol
    boost::random::mt19937 gen(rd());
    boost::random::uniform_int_distribution<> dist(0, 100);

    bool seen_low = false, seen_high = false;
    for (int i = 0; i < 1000; ++i) {
        int v = dist(gen);
        assert(v >= 0 && v <= 100);
        seen_low = seen_low || v == 0;
        seen_high = seen_high || v == 100;
    }
    assert(seen_low && seen_high);

    boost::random::uniform_real_distribution<> dr(0.0, 1.0);
    double x = dr(gen);
    assert(x >= 0.0 && x < 1.0);
    return 0;
}
