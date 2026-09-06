// boost.test smoke — official header-only form: the <boost/test/included/**>
// aggregate (self-contained framework implementation, defines ::main).
// C1 (2026-09-06): boost.test is compiled include-only; without the
// unit_test_framework feature this aggregate IS the library (the official
// optional pure-header configuration). Runs in the default `mcpp test` set.
//
// With --features unit_test_framework the framework TUs compile and link
// into every test program — the aggregate's inline definitions would
// double-define those symbols (M11 §3: the two forms must never link
// together), so this file compiles to a passing stub in that run;
// tests/test_utf.cpp carries the real test there.
#ifdef MCPP_FEATURE_UNIT_TEST_FRAMEWORK

// Feature on: the compiled-form run (see test_utf.cpp) — the framework TUs
// linked into this program would collide with the aggregate below.
int main() { return 0; }

#else

#define BOOST_TEST_MODULE boost_test_included_smoke
#include <boost/test/included/unit_test.hpp>

BOOST_AUTO_TEST_CASE(included_arithmetic) {
    BOOST_TEST(2 + 2 == 4);
    BOOST_CHECK_EQUAL(2 * 3, 6);
}

BOOST_AUTO_TEST_CASE(included_strings) {
    std::string s = "boost";
    BOOST_TEST(s == "boost");
}

#endif
