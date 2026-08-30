// boost.fusion — include-only smoke (M10 T3: macro-driven API surface, no
// module; the import proves import+include mixing in one TU)
#include "test_assert.hpp"
import boost.config;
#include <boost/fusion/include/vector.hpp>
#include <boost/fusion/include/at.hpp>
#include <boost/fusion/include/size.hpp>

int main() {
    boost::fusion::vector<int, double> v(1, 2.5);
    assert(boost::fusion::at_c<0>(v) == 1);
    assert(boost::fusion::at_c<1>(v) == 2.5);
    static_assert(boost::fusion::result_of::size<
                      boost::fusion::vector<int, double>>::value == 2);
    return 0;
}
