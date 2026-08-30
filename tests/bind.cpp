// boost.bind — include-only smoke (M10 T3: macro-driven API surface, no
// module; the import proves import+include mixing in one TU)
#include "test_assert.hpp"
import boost.config;
#include <boost/bind/bind.hpp>

int add(int a, int b) { return a + b; }

int main() {
    using namespace boost::placeholders;
    assert(boost::bind(add, _1, 10)(32) == 42);
    assert(boost::bind(add, 40, _1)(2) == 42);
    return 0;
}
