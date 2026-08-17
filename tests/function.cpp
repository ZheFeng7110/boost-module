// boost.function smoke — polymorphic function wrapper
#include "test_assert.hpp"
import std;
import boost.function;

int main() {
    boost::function<int(int)> f = [](int x) { return x * 2; };
    assert(f(5) == 10);
    boost::function<int(int)> g;
    assert(!g);
    g = f;
    assert(g && g(3) == 6);
    boost::function<void(int&)> h = [](int& x) { x += 1; };
    int v = 1;
    h(v);
    assert(v == 2);
    assert(f.target_type() == g.target_type());
    bool caught = false;
    try {
        boost::function<int(int)> empty;
        empty(1);
    } catch (boost::bad_function_call const&) {
        caught = true;
    }
    assert(caught);
    return 0;
}
