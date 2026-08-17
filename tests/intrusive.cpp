// boost.intrusive smoke — intrusive list with auto_unlink
#include "test_assert.hpp"
import std;
import boost.intrusive;

struct Node : boost::intrusive::list_base_hook<> {
    explicit Node(int v) : value(v) {}
    int value;
    bool operator==(const Node& o) const { return value == o.value; }
};

int main() {
    Node a(1), b(2), c(3);
    boost::intrusive::list<Node> lst;
    lst.push_back(a);
    lst.push_back(b);
    lst.push_back(c);
    assert(lst.size() == 3);
    assert(lst.front().value == 1);
    assert(lst.back().value == 3);
    auto it = lst.begin();
    ++it;
    assert(it->value == 2);
    lst.pop_back();
    assert(lst.size() == 2);
    lst.remove(a);
    assert(lst.size() == 1 && lst.front().value == 2);
    lst.clear();
    assert(lst.empty());
    return 0;
}
