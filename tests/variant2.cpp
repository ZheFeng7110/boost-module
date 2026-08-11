// boost.variant2 smoke — variant, visit, get_if, holds_alternative
#include "test_assert.hpp"
import std;
import boost.variant2;

int main() {
    boost::variant2::variant<int, std::string> v(42);
    assert(boost::variant2::holds_alternative<int>(v));
    assert(boost::variant2::get<int>(v) == 42);
    assert(boost::variant2::get_if<std::string>(&v) == nullptr);
    v = std::string("hi");
    assert(boost::variant2::visit([](auto const& x) {
            if constexpr (std::is_same_v<decltype(x), std::string const&>)
                return static_cast<int>(x.size() + 1);
            else
                return 0;
        }, v) == 3);
    int seen = 0;
    boost::variant2::visit([&seen](auto const&) { ++seen; }, v);
    assert(seen == 1);
    boost::variant2::variant<int, std::string> w(1);
    assert(v != w);
    try {
        (void)boost::variant2::get<int>(v);
        assert(false);
    } catch (boost::variant2::bad_variant_access const&) {
    }
    return 0;
}
