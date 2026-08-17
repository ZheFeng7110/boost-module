// boost.pfr smoke — reflection for aggregate structs
#include "test_assert.hpp"
import std;
import boost.pfr;

struct S {
    int a;
    double b;
    std::string c;
};

int main() {
    S s{1, 2.5, "x"};
    static_assert(boost::pfr::tuple_size<S>::value == 3);
    assert(boost::pfr::get<0>(s) == 1);
    assert(boost::pfr::get<1>(s) == 2.5);
    assert(boost::pfr::get<2>(s) == "x");
    auto t = boost::pfr::structure_to_tuple(s);
    assert(std::get<0>(t) == 1 && std::get<2>(t) == "x");
    boost::pfr::for_each_field(s, [](auto& f) { f = f; });
    assert(boost::pfr::get<0>(s) == 1);
    auto s2 = boost::pfr::structure_tie(s);
    std::get<0>(s2) = 9;
    assert(s.a == 9);
    return 0;
}
