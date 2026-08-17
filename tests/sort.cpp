// boost.sort smoke — spreadsort + pdqsort
#include "test_assert.hpp"
import std;
import boost.sort;

int main() {
    std::vector<unsigned> v{5, 3, 9, 1, 7, 2, 8, 4, 6, 0};
    boost::sort::spreadsort::spreadsort(v.begin(), v.end());
    assert(std::is_sorted(v.begin(), v.end()));
    assert(v.front() == 0 && v.back() == 9);
    std::vector<int> w{10, -3, 7, 1, -8, 4};
    boost::sort::pdqsort(w.begin(), w.end());
    assert(std::is_sorted(w.begin(), w.end()));
    assert(w.front() == -8);
    std::vector<int> x{3, 1, 2};
    boost::sort::block_indirect_sort(x.begin(), x.end(), 2);
    assert(std::is_sorted(x.begin(), x.end()));
    return 0;
}
