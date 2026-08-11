// boost.chrono smoke — compiled lib linkage (clocks/duration arithmetic)
#include "test_assert.hpp"
import std;
import boost.chrono;

int main() {
    boost::chrono::steady_clock::time_point t0 = boost::chrono::steady_clock::now();
    boost::chrono::steady_clock::time_point t1 = boost::chrono::steady_clock::now();
    boost::chrono::nanoseconds ns = t1 - t0;
    assert(ns.count() >= 0);

    boost::chrono::system_clock::time_point tp = boost::chrono::system_clock::now();
    boost::chrono::system_clock::time_point epoch = boost::chrono::system_clock::from_time_t(0);
    boost::chrono::seconds since = boost::chrono::duration_cast<boost::chrono::seconds>(tp - epoch);
    assert(since.count() > 0);

    boost::chrono::seconds a(90);
    boost::chrono::minutes b = boost::chrono::duration_cast<boost::chrono::minutes>(a);
    assert(b.count() == 1);
    assert(boost::chrono::floor<boost::chrono::minutes>(a) == b);
    assert(boost::chrono::ceil<boost::chrono::minutes>(a).count() == 2);
    assert(boost::chrono::round<boost::chrono::minutes>(a).count() == 2);

    boost::chrono::duration<double> d(1.5);
    boost::chrono::milliseconds ms = boost::chrono::duration_cast<boost::chrono::milliseconds>(d);
    assert(ms.count() == 1500);

    boost::chrono::steady_clock::time_point later = t0 + boost::chrono::seconds(1);
    assert(later > t0);
    assert(later - t0 == boost::chrono::seconds(1));

    auto now = boost::chrono::steady_clock::now();
    assert(now.time_since_epoch().count() != 0);
    return 0;
}
