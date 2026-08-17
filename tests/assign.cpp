// boost.assign smoke — list_of / map_list_of / operator+= containers
#include "test_assert.hpp"
import std;
import boost.assign;

int main() {
    std::vector<int> w = boost::assign::list_of(4)(5)(6);
    assert(w.size() == 3 && w[2] == 6);
    std::map<std::string, int> m = boost::assign::map_list_of("a", 1)("b", 2);
    assert(m["a"] == 1 && m["b"] == 2);
    return 0;
}
