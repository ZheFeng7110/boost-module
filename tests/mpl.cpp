// boost.mpl — include-only smoke (M10 T3: config-macro-driven template
// library, user-confirmed include-only; the import proves import+include
// mixing in one TU — mpl deliberately does not include boost/config.hpp,
// which keeps the module/TU attachment overlap minimal)
#include "test_assert.hpp"
#include <type_traits>
import boost.config;
#include <boost/mpl/vector.hpp>
#include <boost/mpl/at.hpp>
#include <boost/mpl/size.hpp>

typedef boost::mpl::vector<int, char, double> seq;
static_assert(boost::mpl::size<seq>::value == 3);
static_assert(std::is_same<boost::mpl::at_c<seq, 1>::type, char>::value);

int main() {
    return 0;
}
