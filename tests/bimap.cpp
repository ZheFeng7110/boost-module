// boost.bimap smoke — bidirectional map
#include "test_assert.hpp"
import std;
import boost.bimap;

int main() {
    boost::bimap<int, std::string> bm;
    bm.insert({1, "one"});
    bm.insert({2, "two"});
    assert(bm.left.count(1) == 1);
    assert(bm.right.count("two") == 1);
    assert(bm.left.at(1) == "one");
    assert(bm.right.at("one") == 1);
    assert(bm.size() == 2);
    auto it = bm.left.find(2);
    assert(it != bm.left.end() && it->second == "two");
    bm.left.erase(1);
    assert(bm.size() == 1 && bm.right.count("one") == 0);
    return 0;
}
