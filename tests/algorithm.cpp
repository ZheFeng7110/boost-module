// boost.algorithm smoke — clamp, hex, minmax, is_palindrome, find, copy_if
import std;
import boost.algorithm;

int main() {
    if (boost::algorithm::clamp(5, 0, 3) != 3) return 1;
    if (boost::algorithm::clamp(-5, 0, 3) != 0) return 2;
    if (boost::algorithm::clamp(2, 0, 3) != 2) return 3;
    std::vector<int> v{1, 3, 2};
    if (boost::algorithm::is_sorted(v.begin(), v.end())) return 4;
    std::sort(v.begin(), v.end());
    if (!boost::algorithm::is_sorted(v.begin(), v.end())) return 5;
    if (!boost::algorithm::is_palindrome(std::string("racecar"))) return 6;
    if (boost::algorithm::is_palindrome(std::string("hello"))) return 7;
    std::string out;
    boost::algorithm::hex(std::string("AB"), std::back_inserter(out));
    if (out != "4142") return 8;
    auto mm = boost::minmax_element(v.begin(), v.end());
    if (*mm.first != 1 || *mm.second != 3) return 9;
    auto pr = boost::minmax(4, 9);
    if (boost::tuples::get<0>(pr) != 4 || boost::tuples::get<1>(pr) != 9) return 10;
    std::vector<int> even;
    boost::algorithm::copy_if(v.begin(), v.end(), std::back_inserter(even),
                              [](int i) { return i % 2 == 0; });
    if (even.size() != 1) return 11;
    if (!boost::algorithm::all_of(v.begin(), v.end(), [](int i) { return i > 0; })) return 12;
    std::vector<int> d{1, 2, 3, 4, 5};
    if (boost::algorithm::find_backward(d, 3) - d.begin() != 2) return 13;
    return 0;
}
