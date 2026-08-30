// boost.function_types — include-only smoke (M10 T3: BOOST_FT_* macro face
// configures the classification templates, no module; the import proves
// import+include mixing in one TU)
#include "test_assert.hpp"
#include <type_traits>
import boost.config;
#include <boost/mpl/size.hpp>
#include <boost/function_types/is_function.hpp>
#include <boost/function_types/result_type.hpp>
#include <boost/function_types/parameter_types.hpp>

static_assert(boost::function_types::is_function<int(float, char)>::value);
static_assert(!boost::function_types::is_function<int (*)(float)>::value);
static_assert(std::is_same<boost::function_types::result_type<
                               int(float, char)>::type,
                           int>::value);
static_assert(boost::mpl::size<boost::function_types::parameter_types<
                   int(float, char)>::type>::value == 2);

int main() {
    return 0;
}
