// boost.variant smoke — recursive variant, get, visitor, comparison
import std;
import boost.variant;

struct visitor : boost::static_visitor<int> {
    int operator()(int i) const { return i + 1; }
    int operator()(std::string const& s) const { return static_cast<int>(s.size()); }
};

int main() {
    boost::variant<int, std::string> v(42);
    if (boost::get<int>(v) != 42) return 1;
    v = std::string("ab");
    if (boost::get<std::string>(v) != "ab") return 2;
    if (boost::apply_visitor(visitor(), v) != 2) return 3;
    boost::variant<int, std::string> w(7);
    if (v == w || !(w < v)) return 4;
    boost::variant<int, std::string> x = v;
    if (v != x) return 5;
    try {
        (void)boost::get<int>(v);
        return 6;
    } catch (boost::bad_get const&) {
    }
    boost::variant<int> only(1);
    if (boost::get<int>(only) != 1) return 7;
    return 0;
}
