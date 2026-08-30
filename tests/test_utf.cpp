// boost.test smoke — compiled Unit Test Framework. The library ships the
// framework TUs but NOT a main (unit_test_main.cpp/cpp_main.cpp are excluded:
// `mcpp test` links every TU into each test program, so a library-provided
// ::main would collide with every consumer's main). The consumer TU owns
// main + the unit_test_main runner: BOOST_TEST_NO_MAIN pulls the runner
// without its main wrapper, BOOST_TEST_MODULE enables the auto-registration
// init glue (unit_test_suite.hpp) and the BOOST_TEST_* macros stay
// include-side (M10 pattern). Exit code 0 == all checks passed.
#define BOOST_TEST_MODULE boost_test_module_smoke
#define BOOST_TEST_NO_MAIN
#include <boost/test/unit_test.hpp>
#include <boost/test/impl/unit_test_main.ipp>
import boost.test;

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
