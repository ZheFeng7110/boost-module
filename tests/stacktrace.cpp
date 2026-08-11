// boost.stacktrace smoke — compiled lib linkage (basic impl, BOOST_STACKTRACE_LINK)
#include "test_assert.hpp"
import std;
import boost.stacktrace;

[[gnu::noinline]] void fill(boost::stacktrace::stacktrace& st) { st = boost::stacktrace::stacktrace(); }

int main() {
    boost::stacktrace::stacktrace st = boost::stacktrace::stacktrace();
    assert(st.size() != 0);
    boost::stacktrace::frame f = st[0];
    assert(f.address() != nullptr);
    std::string s = boost::stacktrace::to_string(st);
    assert(!s.empty());
    std::string f2 = boost::stacktrace::to_string(f);
    assert(!f2.empty());
    boost::stacktrace::stacktrace st2;
    fill(st2);
    assert(st2.size() != 0);
    return 0;
}
