// boost.move smoke — move/forward utilities + movable containers
#include "test_assert.hpp"
import std;
import boost.move;

int main() {
    std::string s("hello");
    std::string t = boost::move(s);
    assert(t == "hello");
    assert(s.empty() || s == "hello");
    std::vector<int> v{1, 2, 3};
    std::vector<int> w = boost::move(v);
    assert(w.size() == 3 && w[0] == 1);
    int x = 5;
    int&& r = boost::forward<int>(x);
    assert(r == 5);
    static_assert(std::is_same<decltype(boost::move_if_noexcept(x)), int&&>::value ||
                  std::is_same<decltype(boost::move_if_noexcept(x)), int&>::value);
    (void)r;
    return 0;
}
