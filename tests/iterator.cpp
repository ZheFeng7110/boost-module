// boost.iterator smoke — counting/transform/filter iterators across module
#include "test_assert.hpp"
import std;
import boost.iterator;

int main() {
    boost::counting_iterator<int> first(1), last(6);
    int sum = 0;
    for (auto it = first; it != last; ++it) sum += *it;
    assert(sum == 15);
    std::vector<int> v{1, 2, 3, 4};
    auto ti = boost::make_transform_iterator(v.begin(), [](int i) { return i * 2; });
    assert(*ti == 2);
    assert(*std::next(ti) == 4);
    auto fi = boost::make_filter_iterator([](int i) { return i % 2 == 0; },
                                          v.begin(), v.end());
    assert(*fi == 2);
    ++fi;
    assert(*fi == 4);
    boost::iterators::iterator_value_t<std::vector<int>::iterator> iv = 5;
    assert(iv == 5);
    auto ci = boost::make_counting_iterator(10);
    assert(*ci == 10);
    return 0;
}
