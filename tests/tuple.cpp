// boost.tuple smoke — tuples, tie, comparison, io manipulators
import std;
import boost.tuple;

int main() {
    boost::tuples::tuple<int, double, std::string> t(1, 2.5, "abc");
    if (boost::tuples::get<0>(t) != 1) return 1;
    if (boost::tuples::get<1>(t) != 2.5) return 2;
    if (boost::tuples::get<2>(t) != "abc") return 3;
    boost::tuples::tuple<int, double, std::string> u = t;
    if (t != u) return 4;
    if (!(t == u)) return 5;
    boost::tuples::tuple<int, double, std::string> v(2, 1.0, "z");
    if (t >= v || !(t < v)) return 6;
    int i = 0;
    double d = 0;
    std::string s;
    boost::tuples::tie(i, d, s) = boost::tuples::make_tuple(7, 8.5, "xy");
    if (i != 7 || d != 8.5 || s != "xy") return 7;
    auto tt = boost::tuples::make_tuple(1, 2);
    if (boost::tuples::get<1>(tt) != 2) return 8;
    std::ostringstream os;
    os << boost::tuples::set_open('[') << boost::tuples::set_close(']')
       << boost::tuples::set_delimiter(';') << t;
    if (os.str() != "[1;2.5;abc]") return 9;
    return 0;
}
