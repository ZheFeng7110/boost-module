// boost.optional smoke — class, make_optional, comparisons, swap, exception
import std;
import boost.optional;

int main() {
    boost::optional<int> a(3);
    boost::optional<int> b = boost::make_optional(4);
    if (!a || !b) return 1;
    if (a == b || !(a < b)) return 2;
    boost::optional<int> c = a;
    if (a != c) return 3;
    boost::swap(a, b);
    if (*a != 4 || *b != 3) return 4;
    if (boost::get_optional_value_or(c, 99) != 3) return 5;
    if (boost::get_optional_value_or(a, 99) != 4) return 6;
    boost::optional<std::string> s("hello");
    if (!(s == std::string("hello"))) return 7;
    bool caught = false;
    try {
        boost::optional<int> empty = boost::none;
        (void)empty.value();
    } catch (boost::bad_optional_access const&) {
        caught = true;
    }
    if (!caught) return 8;
    if (boost::none != boost::optional<int>{}) return 9;
    return 0;
}
