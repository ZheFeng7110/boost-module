// boost.parser smoke — PEG parsing
//
// gcc 16.1.0 blocks the module path: instantiating any exported
// boost.parser entity from the module (parser_interface / directive / parse /
// parser objects) crashes cc1plus with a segfault (gcc modules ICE,
// reproduced on mingw-gcc 16.1.0 and the linux-gcc CI leg). The pure-header
// fallback is also broken on gcc 16.1.0: explicit specializations of the
// constexpr variable template as_utf (search.hpp) are emitted as strong
// symbols, so header + module TU collide with "multiple definition" at link
// time. Until gcc fixes both, the gcc branch just imports the module
// (compile+link coverage; the surface itself is exercised on clang/MSVC).
#include "test_assert.hpp"
#include <cassert>
#if !defined(__GNUC__) || defined(__clang__)
import std;
import boost.parser;
#else
import boost.parser;
static int const parser_link_smoke = 0;
#endif

int main() {
#if !defined(__GNUC__) || defined(__clang__)
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
#else
    (void)parser_link_smoke;
#endif
    return 0;
}
