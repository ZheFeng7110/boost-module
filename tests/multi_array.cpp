// boost.multi_array smoke — N-dimensional array
// boost::extents / boost::indices used to be anonymous-namespace objects
// (internal linkage, no qualified name); the vendored inline patch exports
// them from the module, so the canonical generator spelling works.
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

    // canonical generator spelling now exported: boost::extents[..][..]
    boost::multi_array<double, 2> e(boost::extents[2][3]);
    e[1][2] = 4.5;
    assert(e.shape()[0] == 2 && e.shape()[1] == 3);
    assert(e.num_elements() == 6 && e[1][2] == 4.5);

    // boost::indices is exported as well (index generator object)
    static_assert(std::is_same_v<decltype(boost::indices),
                                 boost::multi_array_types::index_gen>);
    boost::multi_array_types::index_gen ig = boost::indices;
    (void)ig;
    return 0;
}
