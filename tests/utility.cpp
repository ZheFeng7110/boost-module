// boost.utility smoke — compressed_pair, string_view, empty_value
#include "test_assert.hpp"
import std;
import boost.utility;

int main() {
    boost::compressed_pair<int, double> p(1, 2.5);
    assert(p.first() == 1 && p.second() == 2.5);
    static_assert(sizeof(boost::compressed_pair<int, int>) <= sizeof(int) * 2);
    boost::string_view sv("hello world");
    assert(sv.size() == 11);
    assert(sv.substr(0, 5) == "hello");
    assert(sv.starts_with("hello"));
    assert(sv.ends_with("world"));
    boost::string_view sv2 = boost::string_view("abc").substr(1);
    assert(sv2 == "bc");
    assert(boost::string_view("a") < boost::string_view("b"));
    return 0;
}
