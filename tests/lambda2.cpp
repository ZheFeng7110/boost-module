// boost.lambda2 — include-only smoke (M10 T3: macro-driven API surface, no
// module; the import proves import+include mixing in one TU)
#include "test_assert.hpp"
import boost.config;
#include <boost/lambda2.hpp>

int main() {
    assert((boost::lambda2::_1 + 1)(41) == 42);
    assert((boost::lambda2::_1 * boost::lambda2::_2)(6, 7) == 42);
    return 0;
}
