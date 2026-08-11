// boost.variant smoke — recursive variant, get, visitor, comparison
#include "test_assert.hpp"
import std;
import boost.variant;

struct visitor : boost::static_visitor<int> {
    int operator()(int i) const { return i + 1; }
    int operator()(std::string const& s) const { return static_cast<int>(s.size()); }
};

int main() {
    boost::variant<int, std::string> v(42);
    assert(boost::get<int>(v) == 42);
    v = std::string("ab");
    assert(boost::get<std::string>(v) == "ab");
    assert(boost::apply_visitor(visitor(), v) == 2);
    boost::variant<int, std::string> w(7);
    assert(v != w && w < v);
    boost::variant<int, std::string> x = v;
    assert(v == x);
    try {
        (void)boost::get<int>(v);
        assert(false);
    } catch (boost::bad_get const&) {
    }
    boost::variant<int> only(1);
    assert(boost::get<int>(only) == 1);
    return 0;
}
