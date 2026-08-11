// boost.static_string smoke — fixed-capacity string
#include "test_assert.hpp"
import std;
import boost.static_string;

int main() {
    boost::static_string<16> s("hello");
    s += " world";
    assert(s.size() == 11 && s.capacity() == 16);
    assert(s == "hello world");
    assert(s.compare("hello world") == 0);
    assert(s < "zebra");
    boost::static_string<16> t = s;
    assert(t == s);
    t.append("!");
    assert(t.front() == 'h' && t.back() == '!');
    boost::static_string<8> u;
    u = "abcd";
    assert(u.size() == 4);
    boost::static_string<16> v(s, 0, 5);
    assert(v == "hello");
    std::string st = s.c_str();
    assert(st == "hello world");
    return 0;
}
