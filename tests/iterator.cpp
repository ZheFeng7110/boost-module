// boost.iterator smoke — counting/transform/filter iterators across module
import std;
import boost.iterator;

int main() {
    boost::counting_iterator<int> first(1), last(6);
    int sum = 0;
    for (auto it = first; it != last; ++it) sum += *it;
    if (sum != 15) return 1;
    std::vector<int> v{1, 2, 3, 4};
    auto ti = boost::make_transform_iterator(v.begin(), [](int i) { return i * 2; });
    if (*ti != 2) return 2;
    if (*std::next(ti) != 4) return 3;
    auto fi = boost::make_filter_iterator([](int i) { return i % 2 == 0; },
                                          v.begin(), v.end());
    if (*fi != 2) return 4;
    ++fi;
    if (*fi != 4) return 5;
    boost::iterators::iterator_value_t<std::vector<int>::iterator> iv = 5;
    if (iv != 5) return 6;
    auto ci = boost::make_counting_iterator(10);
    if (*ci != 10) return 7;
    return 0;
}
