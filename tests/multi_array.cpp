// boost.multi_array smoke — N-dimensional array
#include "test_assert.hpp"
import std;
import boost.multi_array;

int main() {
    boost::array<boost::multi_array<double, 2>::size_type, 2> dims = {{2, 3}};
    boost::multi_array<double, 2> a(dims);
    assert(a.shape()[0] == 2 && a.shape()[1] == 3);
    a[0][0] = 1.5;
    a[1][2] = 4.5;
    assert(a[0][0] == 1.5 && a[1][2] == 4.5);
    assert(a.num_dimensions() == 2);
    assert(a.num_elements() == 6);
    double total = 0;
    for (std::size_t i = 0; i < 2; ++i) {
        for (std::size_t j = 0; j < 3; ++j) {
            total += a[i][j];
        }
    }
    assert(total == 6.0);
    assert(a.shape()[0] == 2 && a.shape()[1] == 3);
    boost::array<boost::multi_array<int, 3>::size_type, 3> dims3 = {{2, 2, 2}};
    boost::multi_array<int, 3> cube(dims3);
    cube[0][1][1] = 7;
    assert(cube[0][1][1] == 7 && cube.num_elements() == 8);
    return 0;
}
