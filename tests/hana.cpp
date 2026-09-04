// boost.hana smoke — hana::tuple / integral_constant / algorithms
// (variable templates like int_c/integral_c are not module-exportable — M9 §6,
// libclang exposes no variable-template cursors — so the class-template
// integral_constant spelling is used)
// NB: no `import std;` here — the std::integral_constant base that comes in
// through the std CMI mismatches the one recorded in the boost.hana CMI and
// runtime comparisons of integral_constants misbehave (M9 §4 trap variant).
#include "test_assert.hpp"
import boost.hana;

int main() {
    namespace hana = boost::hana;

    constexpr auto tup = hana::make_tuple(1, 'x', 2.0);
    static_assert(decltype(hana::size(tup))::value == 3u);
    assert(hana::at_c<0>(tup) == 1);
    assert(hana::at_c<1>(tup) == 'x');

    constexpr auto one = hana::integral_constant<int, 1>{};
    constexpr auto two = hana::integral_constant<int, 2>{};
    static_assert(decltype(one + two)::value == 3);

    constexpr auto xs = hana::make_tuple(hana::integral_constant<int, 2>{},
                                         hana::integral_constant<int, 1>{},
                                         hana::integral_constant<int, 3>{});
    constexpr auto sorted = hana::sort(xs);
    // explicit bool cast: the MSVC assert macro expands to `(!!(e)) || ...`
    // and `!` picks up hana's user-defined operator! (which misbehaves in a
    // module consumer TU) — the same MSVC-assert trap as the M9 tribool case
    assert((bool)(hana::at_c<0>(sorted) == hana::integral_constant<int, 1>{}));
    assert((bool)(hana::at_c<2>(sorted) == hana::integral_constant<int, 3>{}));
    return 0;
}
