// boost.flyweight smoke — flyweight string sharing
#include "test_assert.hpp"
import std;
import boost.flyweight;

int main() {
    boost::flyweight<std::string> a("hello");
    boost::flyweight<std::string> b("hello");
    boost::flyweight<std::string> c("world");
    assert(a == b);
    assert(a != c);
    assert(&a.get() == &b.get());
    assert(&a.get() != &c.get());
    boost::flyweight<std::string> d = a;
    assert(d == a && &d.get() == &a.get());
    assert(a.get() == "hello");
    return 0;
}
