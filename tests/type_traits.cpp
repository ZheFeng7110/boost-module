// boost.type_traits smoke — trait correctness across the module boundary
import std;
import boost.type_traits;

int main() {
    static_assert(boost::is_integral<int>::value);
    static_assert(!boost::is_integral<float>::value);
    static_assert(boost::is_same<int, boost::remove_const<const int>::type>::value);
    static_assert(boost::is_same<const int, boost::add_const<int>::type>::value);
    static_assert(boost::is_same<int*, boost::add_pointer<int>::type>::value);
    static_assert(boost::is_same<int&, boost::add_lvalue_reference<int>::type>::value);
    static_assert(boost::is_same<int, boost::remove_reference<int&>::type>::value);
    static_assert(boost::is_same<unsigned, boost::make_unsigned<int>::type>::value);
    static_assert(boost::is_same<signed, boost::make_signed<unsigned>::type>::value);
    static_assert(boost::alignment_of<double>::value >= 4);
    static_assert(boost::is_convertible<int, double>::value);
    static_assert(boost::is_base_of<std::ios_base, std::ostream>::value);
    static_assert(boost::is_class<std::string>::value);
    static_assert(boost::has_trivial_copy<int>::value);
    static_assert(boost::is_unsigned<unsigned long>::value);
    if (!boost::is_integral<long>::value) return 1;
    return 0;
}
