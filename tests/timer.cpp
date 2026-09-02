// boost.timer smoke — compiled lib linkage (cpu_timer / auto_timers TUs)
#include "test_assert.hpp"
import std;
import boost.timer;

int main() {
    boost::timer::cpu_timer t;   // ctor auto-starts
    volatile long long acc = 0;
    for (int i = 0; i < 10000; ++i) acc += i;
    // POSIX wall comes from times() (_SC_CLK_TCK == 100 -> 10ms resolution);
    // a loop this short can finish within one tick and elapsed().wall == 0.
    // Give the clock at least a few ticks before stopping.
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    t.stop();
    boost::timer::cpu_times times = t.elapsed();
    assert(times.wall > 0);
    assert(!t.format().empty());

    boost::timer::cpu_timer t2;  // auto_timers_construction.cpp TU symbols
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    t2.stop();
    assert(t2.elapsed().wall > 0);
    return 0;
}
