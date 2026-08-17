// boost.signals2 smoke — signals and slots
#include "test_assert.hpp"
import std;
import boost.signals2;

int main() {
    boost::signals2::signal<int(int)> sig;
    int total = 0;
    sig.connect([&](int x) { total += x; return 0; });
    sig.connect([&](int x) { total += x * 2; return 0; });
    sig(10);
    assert(total == 30);
    assert(sig.num_slots() == 2);
    auto conn = sig.connect([&](int x) { total += 100; return 0; });
    sig(1);
    assert(total == 133);
    conn.disconnect();
    assert(sig.num_slots() == 2);
    boost::signals2::signal<void()> sig2;
    int calls = 0;
    sig2.connect([&] { ++calls; });
    sig2();
    assert(calls == 1);
    sig2.disconnect_all_slots();
    sig2();
    assert(calls == 1);
    return 0;
}
