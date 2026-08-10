// boost.variant2 smoke — variant, visit, get_if, holds_alternative
import std;
import boost.variant2;

int main() {
    boost::variant2::variant<int, std::string> v(42);
    if (!boost::variant2::holds_alternative<int>(v)) return 1;
    if (boost::variant2::get<int>(v) != 42) return 2;
    if (boost::variant2::get_if<std::string>(&v) != nullptr) return 3;
    v = std::string("hi");
    if (boost::variant2::visit([](auto const& x) {
            if constexpr (std::is_same_v<decltype(x), std::string const&>)
                return static_cast<int>(x.size() + 1);
            else
                return 0;
        }, v) != 3) return 4;
    int seen = 0;
    boost::variant2::visit([&seen](auto const&) { ++seen; }, v);
    if (seen != 1) return 5;
    boost::variant2::variant<int, std::string> w(1);
    if (v == w) return 6;
    try {
        (void)boost::variant2::get<int>(v);
        return 7;
    } catch (boost::variant2::bad_variant_access const&) {
    }
    return 0;
}
