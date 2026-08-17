// boost.leaf smoke — error handling with result / try_handle_all
#include "test_assert.hpp"
import std;
import boost.leaf;

int main() {
    auto read = [](int x) -> boost::leaf::result<int> {
        if (x < 0) {
            return boost::leaf::new_error(std::runtime_error("negative"));
        }
        return x * 2;
    };
    auto r = read(5);
    assert(r);
    assert(r.value() == 10);
    int out = boost::leaf::try_handle_all(
        [&]() -> boost::leaf::result<int> { return read(-1); },
        [](boost::leaf::error_info const&) { return -1; },
        [] { return -2; });
    assert(out == -1);
    int out2 = boost::leaf::try_handle_all(
        [&]() -> boost::leaf::result<int> { return read(7); },
        [](boost::leaf::error_info const&) { return -1; },
        [] { return -2; });
    assert(out2 == 14);
    return 0;
}
