// boost.test smoke — compiled Unit Test Framework form (the official
// recommended configuration). C1 (2026-09-06): boost.test is compiled
// include-only — the feature (renamed unit_test_framework, aligned with the
// upstream CMake target) ships the framework TUs but NO module; there is no
// `import boost.test`. The consumer TU owns main + the unit_test_main runner:
// BOOST_TEST_NO_MAIN pulls the runner without its main wrapper,
// BOOST_TEST_MODULE enables the auto-registration init glue
// (unit_test_suite.hpp) and the BOOST_TEST_* macros stay include-side (M10
// pattern). Exit code 0 == all checks passed.
//
// The two Unit Test Framework forms must never link together (the framework
// TUs and the <boost/test/included/**> aggregate double-define the framework
// symbols, M11 §3), so this file compiles to a passing stub when the feature
// is off — tests/test_included.cpp carries the real test in that run
// (MCPP_FEATURE_<NAME> is defined for every active feature, verified 2026-09-06).
#ifdef MCPP_FEATURE_UNIT_TEST_FRAMEWORK

#define BOOST_TEST_MODULE boost_test_module_smoke
#define BOOST_TEST_NO_MAIN
#include <boost/test/unit_test.hpp>
#include <boost/test/impl/unit_test_main.ipp>

BOOST_AUTO_TEST_CASE(arithmetic) {
    BOOST_TEST(1 + 1 == 2);
    BOOST_CHECK_EQUAL(3 * 3, 9);
}

BOOST_AUTO_TEST_CASE(strings) {
    std::string s = "boost";
    BOOST_TEST(s == "boost");
}

int main(int argc, char* argv[]) {
    return boost::unit_test::unit_test_main(&init_unit_test_suite, argc, argv);
}

#else

// Feature off: the header-only form's run (see test_included.cpp). The
// framework TUs are not compiled in this build, so there is nothing to
// exercise here — pass and stay out of the way.
int main() { return 0; }

#endif
