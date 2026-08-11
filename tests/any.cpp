// boost.any smoke — any, any_cast (value/ref/pointer), empty
#include "test_assert.hpp"
import std;
import boost.any;

int main() {
    boost::any a(5);
    assert(boost::any_cast<int>(a) == 5);
    boost::any b(std::string("abc"));
    assert(boost::any_cast<std::string>(b) == "abc");
    boost::any_cast<std::string&>(b) = "xyz";
    assert(boost::any_cast<std::string>(b) == "xyz");
    assert(boost::any_cast<int>(&b) == nullptr);
    assert(*boost::any_cast<std::string>(&b) == "xyz");
    try {
        (void)boost::any_cast<int>(b);
        assert(false);
    } catch (boost::bad_any_cast const&) {
    }
    boost::any empty;
    assert(empty.empty());
    boost::any c = b;
    assert(boost::any_cast<std::string>(c) == "xyz");
    return 0;
}
