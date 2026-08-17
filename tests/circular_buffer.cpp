// boost.circular_buffer smoke — circular buffer container
#include "test_assert.hpp"
import std;
import boost.circular_buffer;

int main() {
    boost::circular_buffer<int> cb(3);
    assert(cb.empty());
    cb.push_back(1);
    cb.push_back(2);
    cb.push_back(3);
    assert(cb.full());
    assert(cb[0] == 1 && cb[2] == 3);
    cb.push_back(4);
    assert(cb.full() && cb.front() == 2 && cb.back() == 4);
    assert(cb.size() == 3);
    cb.pop_front();
    assert(cb.front() == 3 && cb.size() == 2);
    assert(cb.capacity() == 3);
    cb.push_front(9);
    assert(cb.front() == 9);
    return 0;
}
