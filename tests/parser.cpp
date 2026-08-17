// boost.parser smoke — PEG parsing
#include "test_assert.hpp"
import std;
import boost.parser;

int main() {
    namespace bp = boost::parser;
    auto r = bp::parse("12345", bp::uint_);
    assert(r);
    assert(*r == 12345u);
    auto r2 = bp::parse("42.5", bp::double_);
    assert(r2 && *r2 == 42.5);
    auto r3 = bp::parse("a123",
                        bp::char_("a-z") >> +bp::digit, bp::ws);
    assert(r3);
    assert(r3->size() == 4);
    assert((*r3)[0] == 'a');
    auto r4 = bp::parse("not-a-number", bp::uint_);
    assert(!r4);
    auto r5 = bp::parse("hello", bp::string("hello"));
    assert(r5 && *r5 == "hello");
    return 0;
}
