// boost.phoenix — include-only smoke (M10 T3: macro-driven API surface, no
// module; the import proves import+include mixing in one TU)
#include "test_assert.hpp"
#include <algorithm>
#include <vector>
import boost.config;
#include <boost/phoenix/phoenix.hpp>

int main() {
    assert(boost::phoenix::val(42)() == 42);
    using boost::phoenix::arg_names::arg1;
    assert((arg1 * 2)(21) == 42);
    std::vector<int> v;
    v.push_back(1);
    v.push_back(2);
    std::transform(v.begin(), v.end(), v.begin(), arg1 * 10);
    assert(v[0] == 10 && v[1] == 20);
    return 0;
}
