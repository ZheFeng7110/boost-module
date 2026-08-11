// boost.range smoke — ranges, adaptors (function forms), algorithms on ranges
#include "test_assert.hpp"
import std;
import boost.range;

int main() {
    std::vector<int> v{3, 1, 4, 1, 5};
    auto rng = boost::make_iterator_range(v);
    assert(boost::size(rng) == 5);
    assert(*boost::begin(rng) == 3);
    assert(*boost::prior(boost::end(rng)) == 5);
    assert(boost::count(rng, 1) == 2);
    auto it = boost::find(rng, 4);
    assert(it != boost::end(rng));
    std::vector<int> out;
    boost::copy(boost::adaptors::reverse(rng), std::back_inserter(out));
    assert(out == std::vector<int>({5, 1, 4, 1, 3}));
    auto ir = boost::irange(0, 4);
    assert(boost::size(ir) == 4);
    out.clear();
    boost::copy(boost::adaptors::filter(rng, [](int i) { return i > 2; }),
                std::back_inserter(out));
    assert(out == std::vector<int>({3, 4, 5}));
    out.clear();
    boost::copy(boost::adaptors::transform(rng, [](int i) { return i + 1; }),
                std::back_inserter(out));
    assert(out == std::vector<int>({4, 2, 5, 2, 6}));
    auto me = boost::max_element(rng);
    assert(me != boost::end(rng) && *me == 5);
    assert(boost::accumulate(rng, 0) == 14);
    assert(boost::as_literal("abc").size() == 3);
    return 0;
}
