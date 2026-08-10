// boost.core smoke — exchange, ignore_unused, core::swap, version constexpr
import std;
import boost.core;

int main() {
    int x = 1;
    int old = boost::exchange(x, 2);
    if (old != 1 || x != 2) return 1;
    boost::ignore_unused(old, x);
    int a = 5, b = 9;
    boost::swap(a, b);
    if (a != 9 || b != 5) return 2;
    boost::swap(a, b);
    if (a != 5 || b != 9) return 3;
    if (boost::BOOST_VERSION != 109100) return 4;
    static_assert(boost::BOOST_VERSION == 109100);
    static_assert(boost::BOOST_LIB_VERSION[0] == '1');
    boost::empty_value<int> ev(boost::empty_init, 7);
    if (ev.get() != 7) return 5;
    return 0;
}
