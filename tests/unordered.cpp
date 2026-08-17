// boost.unordered smoke — boost unordered containers
#include "test_assert.hpp"
import std;
import boost.unordered;

int main() {
    boost::unordered::unordered_map<std::string, int> m;
    m["a"] = 1;
    m["b"] = 2;
    assert(m.size() == 2);
    assert(m["a"] == 1);
    assert(m.at("b") == 2);
    assert(m.find("c") == m.end());
    assert(m.count("a") == 1);
    m.erase("a");
    assert(m.size() == 1 && m.count("a") == 0);
    boost::unordered::unordered_set<int> s;
    s.insert(1);
    s.insert(2);
    s.insert(2);
    assert(s.size() == 2);
    assert(s.count(1) == 1 && s.count(3) == 0);
    assert(s.erase(2) == 1);
    assert(s.load_factor() > 0.0f);
    return 0;
}
