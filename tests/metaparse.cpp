// boost.metaparse — include-only smoke (M10 T3: BOOST_METAPARSE_STRING and
// the 2.4k-macro parser-building face, no module; the import proves
// import+include mixing in one TU)
#include "test_assert.hpp"
#include <type_traits>
import boost.config;
#include <boost/metaparse/string.hpp>

typedef BOOST_METAPARSE_STRING("hi") via_macro;
typedef boost::metaparse::string<'h', 'i'> manual;
static_assert(std::is_same<via_macro, manual>::value);

int main() {
    return 0;
}
