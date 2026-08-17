// boost.yap smoke — expression templates
#include "test_assert.hpp"
import std;
import boost.yap;

int main() {
    namespace yap = boost::yap;
    auto expr = yap::make_terminal(5) + yap::make_terminal(3);
    int v = yap::evaluate(expr);
    assert(v == 8);
    auto expr2 = yap::make_terminal(5) * yap::make_terminal(2) + yap::make_terminal(1);
    assert(yap::evaluate(expr2) == 11);
    auto t = yap::make_terminal(7);
    assert(yap::evaluate(t) == 7);
    auto expr3 = (yap::make_terminal(10) - yap::make_terminal(4)) / yap::make_terminal(2);
    assert(yap::evaluate(expr3) == 3);
    return 0;
}
