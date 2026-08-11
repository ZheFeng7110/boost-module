// boost.mp11 smoke — metaprogramming: list ops, aliases, maps, transforms
#include "test_assert.hpp"
import std;
import boost.mp11;

using namespace boost::mp11;

int main() {
    using L = mp_list<int, float, double>;
    static_assert(mp_size<L>::value == 3);
    static_assert(std::is_same_v<mp_at_c<L, 0>, int>);
    static_assert(std::is_same_v<mp_at_c<L, 2>, double>);
    static_assert(std::is_same_v<mp_at<L, mp_int<1>>, float>);
    static_assert(std::is_same_v<mp_first<L>, int>);
    static_assert(std::is_same_v<mp_second<L>, float>);
    static_assert(std::is_same_v<mp_append<L, mp_list<char>>, mp_list<int, float, double, char>>);
    static_assert(std::is_same_v<mp_push_back<L, char>, mp_list<int, float, double, char>>);
    static_assert(std::is_same_v<mp_transform<std::add_pointer_t, L>, mp_list<int*, float*, double*>>);
    using M = mp_list<mp_list<int, float>, mp_list<char, double>>;
    static_assert(std::is_same_v<mp_map_find<M, char>, mp_list<char, double>>);
    static_assert(mp_map_contains<M, int>::value);
    static_assert(!mp_map_contains<M, bool>::value);
    static_assert(std::is_same_v<mp_iota_c<3>, mp_list<mp_size_t<0>, mp_size_t<1>, mp_size_t<2>>>);
    static_assert(mp_count_if<L, std::is_floating_point>::value == 2);
    static_assert(mp_any_of<L, std::is_integral>::value);
    static_assert(mp_all_of<L, std::is_arithmetic>::value);
    using IL = mp_list<mp_int<3>, mp_int<1>, mp_int<2>>;
    using SR = mp_sort<IL, mp_less>;
    static_assert(std::is_same_v<SR, mp_list<mp_int<1>, mp_int<2>, mp_int<3>>>);
    int sum = 0;
    mp_for_each<L>([&sum](auto const&) { ++sum; });
    assert(sum == 3);
    return 0;
}
