// boost.lambda — include-only smoke (M10 T3: macro-driven API surface, no
// module; the import proves import+include mixing in one TU)
#include "test_assert.hpp"
#include <algorithm>
#include <vector>
import boost.config;
#include <boost/lambda/lambda.hpp>

int main() {
    std::vector<int> v;
    v.push_back(1);
    v.push_back(2);
    v.push_back(3);
    int total = 0;
    std::for_each(v.begin(), v.end(), total += boost::lambda::_1);
    assert(total == 6);
    return 0;
}
