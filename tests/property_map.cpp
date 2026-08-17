// boost.property_map smoke — property map adapters
#include "test_assert.hpp"
import std;
import boost.property_map;

int main() {
    boost::identity_property_map id;
    assert(id[42] == 42);
    assert(boost::get(id, 10) == 10);
    std::vector<int> v{10, 20, 30};
    boost::iterator_property_map<decltype(v)::iterator,
                                 boost::identity_property_map> pm(v.begin());
    assert(boost::get(pm, 1) == 20);
    assert(v[1] == 20);
    std::map<std::string, int> m{{"a", 1}};
    auto mp = boost::make_assoc_property_map(m);
    assert(boost::get(mp, "a") == 1);
    return 0;
}
