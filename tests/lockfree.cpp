// boost.lockfree smoke — lock-free stack
#include "test_assert.hpp"
import std;
import boost.lockfree;

int main() {
    boost::lockfree::stack<int> st(8);
    assert(st.push(1));
    assert(st.push(2));
    assert(st.push(3));
    int v = 0;
    assert(st.pop(v) && v == 3);
    assert(st.pop(v) && v == 2);
    assert(st.pop(v) && v == 1);
    assert(!st.pop(v));
    assert(st.empty());
    boost::lockfree::queue<int> q(8);
    assert(q.push(10));
    assert(q.push(20));
    assert(q.pop(v) && v == 10);
    assert(q.pop(v) && v == 20);
    return 0;
}
