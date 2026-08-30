// boost.timer smoke — compiled lib linkage (cpu_timer / auto_timers TUs)
#include "test_assert.hpp"
import std;
import boost.timer;

int main() {
    boost::timer::cpu_timer t;   // ctor auto-starts
    volatile long long acc = 0;
    for (int i = 0; i < 10000; ++i) acc += i;
    t.stop();
    boost::timer::cpu_times times = t.elapsed();
    assert(times.wall > 0);
    assert(!t.format().empty());

    boost::timer::cpu_timer t2;  // auto_timers_construction.cpp TU symbols
    t2.stop();
    assert(t2.elapsed().wall > 0);
    return 0;
}
