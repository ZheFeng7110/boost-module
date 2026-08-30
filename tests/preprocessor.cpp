// boost.preprocessor — include-only smoke (M10 T3: the whole API is the
// BOOST_PP_* macro family, 22.9k macros — a named module can never export
// macros, so consumers #include; the import proves import+include mixing)
#include "test_assert.hpp"
#include <cstring>
import boost.config;
#include <boost/preprocessor/cat.hpp>
#include <boost/preprocessor/stringize.hpp>
#include <boost/preprocessor/variadic/size.hpp>
#include <boost/preprocessor/arithmetic/inc.hpp>

static_assert(BOOST_PP_CAT(1, 2) == 12);
static_assert(BOOST_PP_INC(41) == 42);
static_assert(BOOST_PP_VARIADIC_SIZE(a, b, c) == 3);
#define M10_TOKEN hello
const char* s = BOOST_PP_STRINGIZE(M10_TOKEN);

int main() {
    assert(std::strcmp(s, "hello") == 0);
    return 0;
}
