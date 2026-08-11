// boost.optional smoke — class, make_optional, comparisons, swap, exception
#include "test_assert.hpp"
import std;
import boost.optional;

int main() {
    boost::optional<int> a(3);
    boost::optional<int> b = boost::make_optional(4);
    assert(a && b);
    assert(a != b && a < b);
    boost::optional<int> c = a;
    assert(a == c);
    boost::swap(a, b);
    assert(*a == 4 && *b == 3);
    assert(boost::get_optional_value_or(c, 99) == 3);
    assert(boost::get_optional_value_or(a, 99) == 4);
    boost::optional<std::string> s("hello");
    assert(s == std::string("hello"));
    bool caught = false;
    try {
        boost::optional<int> empty = boost::none;
        (void)empty.value();
    } catch (boost::bad_optional_access const&) {
        caught = true;
    }
    assert(caught);
    assert(boost::none == boost::optional<int>{});
    return 0;
}
