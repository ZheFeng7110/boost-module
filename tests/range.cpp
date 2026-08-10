// boost.range smoke — ranges, adaptors (function forms), algorithms on ranges
import std;
import boost.range;

int main() {
    std::vector<int> v{3, 1, 4, 1, 5};
    auto rng = boost::make_iterator_range(v);
    if (boost::size(rng) != 5) return 1;
    if (*boost::begin(rng) != 3) return 2;
    if (*boost::prior(boost::end(rng)) != 5) return 3;
    if (boost::count(rng, 1) != 2) return 4;
    auto it = boost::find(rng, 4);
    if (it == boost::end(rng)) return 5;
    std::vector<int> out;
    boost::copy(boost::adaptors::reverse(rng), std::back_inserter(out));
    if (out != std::vector<int>({5, 1, 4, 1, 3})) return 6;
    auto ir = boost::irange(0, 4);
    if (boost::size(ir) != 4) return 7;
    out.clear();
    boost::copy(boost::adaptors::filter(rng, [](int i) { return i > 2; }),
                std::back_inserter(out));
    if (out != std::vector<int>({3, 4, 5})) return 8;
    out.clear();
    boost::copy(boost::adaptors::transform(rng, [](int i) { return i + 1; }),
                std::back_inserter(out));
    if (out != std::vector<int>({4, 2, 5, 2, 6})) return 9;
    auto me = boost::max_element(rng);
    if (me == boost::end(rng) || *me != 5) return 10;
    if (boost::accumulate(rng, 0) != 14) return 11;
    if (boost::as_literal("abc").size() != 3) return 12;
    return 0;
}
