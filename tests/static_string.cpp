// boost.static_string smoke — fixed-capacity string
import std;
import boost.static_string;

int main() {
    boost::static_string<16> s("hello");
    s += " world";
    if (s.size() != 11 || s.capacity() != 16) return 1;
    if (s != "hello world") return 2;
    if (s.compare("hello world") != 0) return 3;
    if (!(s < "zebra")) return 4;
    boost::static_string<16> t = s;
    if (t != s) return 5;
    t.append("!");
    if (t.front() != 'h' || t.back() != '!') return 6;
    boost::static_string<8> u;
    u = "abcd";
    if (u.size() != 4) return 7;
    boost::static_string<16> v(s, 0, 5);
    if (v != "hello") return 8;
    std::string st = s.c_str();
    if (st != "hello world") return 9;
    return 0;
}
