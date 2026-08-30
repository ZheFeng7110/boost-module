// boost.foreach — include-only smoke (M10 T3: BOOST_FOREACH is a macro, no
// module; the import proves import+include mixing in one TU)
#include "test_assert.hpp"
#include <vector>
import boost.config;
#include <boost/foreach.hpp>

int main() {
    std::vector<int> v;
    v.push_back(1);
    v.push_back(2);
    v.push_back(3);
    int sum = 0;
    BOOST_FOREACH (int x, v) {
        sum += x;
    }
    assert(sum == 6);
    return 0;
}
