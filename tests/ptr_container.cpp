// boost.ptr_container smoke — pointer containers
#include "test_assert.hpp"
import std;
import boost.ptr_container;

int main() {
    boost::ptr_vector<int> v;
    v.push_back(new int(42));
    v.push_back(new int(7));
    assert(v.size() == 2);
    assert(v[0] == 42 && v[1] == 7);
    v[1] = 99;
    assert(v[1] == 99);
    assert(v.front() == 42 && v.back() == 99);
    boost::ptr_map<std::string, int> m;
    m["a"] = 1;
    m["b"] = 2;
    assert(m["a"] == 1 && m["b"] == 2);
    assert(m.size() == 2);
    v.clear();
    assert(v.empty());
    return 0;
}
