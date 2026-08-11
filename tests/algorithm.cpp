// boost.algorithm smoke — clamp, hex, minmax, is_palindrome, find, copy_if
#include "test_assert.hpp"
import std;
import boost.algorithm;

int main() {
    assert(boost::algorithm::clamp(5, 0, 3) == 3);
    assert(boost::algorithm::clamp(-5, 0, 3) == 0);
    assert(boost::algorithm::clamp(2, 0, 3) == 2);
    std::vector<int> v{1, 3, 2};
    assert(!boost::algorithm::is_sorted(v.begin(), v.end()));
    std::sort(v.begin(), v.end());
    assert(boost::algorithm::is_sorted(v.begin(), v.end()));
    assert(boost::algorithm::is_palindrome(std::string("racecar")));
    assert(!boost::algorithm::is_palindrome(std::string("hello")));
    std::string out;
    boost::algorithm::hex(std::string("AB"), std::back_inserter(out));
    assert(out == "4142");
    auto mm = boost::minmax_element(v.begin(), v.end());
    assert(*mm.first == 1 && *mm.second == 3);
    auto pr = boost::minmax(4, 9);
    assert(boost::tuples::get<0>(pr) == 4 && boost::tuples::get<1>(pr) == 9);
    std::vector<int> even;
    boost::algorithm::copy_if(v.begin(), v.end(), std::back_inserter(even),
                              [](int i) { return i % 2 == 0; });
    assert(even.size() == 1);
    assert(boost::algorithm::all_of(v.begin(), v.end(), [](int i) { return i > 0; }));
    std::vector<int> d{1, 2, 3, 4, 5};
    assert(boost::algorithm::find_backward(d, 3) - d.begin() == 2);
    return 0;
}
