// boost.heap smoke — priority queue / binomial heap
#include "test_assert.hpp"
import std;
import boost.heap;

int main() {
    boost::heap::priority_queue<int> pq;
    pq.push(3);
    pq.push(1);
    pq.push(4);
    assert(pq.top() == 4);
    assert(pq.size() == 3);
    pq.pop();
    assert(pq.top() == 3);
    boost::heap::binomial_heap<int> bh;
    auto it = bh.push(10);
    bh.push(5);
    assert(bh.top() == 10);
    bh.update(it, 20);
    assert(bh.top() == 20);
    assert(bh.size() == 2);
    bh.erase(it);
    assert(bh.top() == 5);
    return 0;
}
