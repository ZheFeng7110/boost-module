// boost.tuple smoke — tuples, tie, comparison, io manipulators
#include "test_assert.hpp"
import std;
import boost.tuple;

int main() {
    boost::tuples::tuple<int, double, std::string> t(1, 2.5, "abc");
    assert(boost::tuples::get<0>(t) == 1);
    assert(boost::tuples::get<1>(t) == 2.5);
    assert(boost::tuples::get<2>(t) == "abc");
    boost::tuples::tuple<int, double, std::string> u = t;
    assert(t == u);
    assert(t == u);
    boost::tuples::tuple<int, double, std::string> v(2, 1.0, "z");
    assert(t < v);
    int i = 0;
    double d = 0;
    std::string s;
    boost::tuples::tie(i, d, s) = boost::tuples::make_tuple(7, 8.5, "xy");
    assert(i == 7 && d == 8.5 && s == "xy");
    auto tt = boost::tuples::make_tuple(1, 2);
    assert(boost::tuples::get<1>(tt) == 2);
    std::ostringstream os;
    os << boost::tuples::set_open('[') << boost::tuples::set_close(']')
       << boost::tuples::set_delimiter(';') << t;
    assert(os.str() == "[1;2.5;abc]");
    return 0;
}
