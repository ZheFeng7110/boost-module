// boost.array smoke — boost::array container
#include "test_assert.hpp"
import std;
import boost.array;

int main() {
    boost::array<int, 3> a = {{1, 2, 3}};
    assert(a.size() == 3);
    assert(a[1] == 2);
    assert(a.at(2) == 3);
    assert(a.front() == 1 && a.back() == 3);
    assert(boost::get<1>(a) == 2);
    bool caught = false;
    try {
        (void)a.at(5);
    } catch (std::out_of_range const&) {
        caught = true;
    }
    assert(caught);
    int c[3] = {4, 5, 6};
    boost::array<int, 3> b = boost::to_array(c);
    assert(b[0] == 4 && b[2] == 6);
    assert(a != b);
    assert(boost::get_c_array(a)[0] == 1);
    a.fill(9);
    assert(a[0] == 9 && a[2] == 9);
    return 0;
}
