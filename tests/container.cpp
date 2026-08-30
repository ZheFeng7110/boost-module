// boost.container smoke — compiled lib linkage (pmr global_resource /
// monotonic_buffer_resource TUs)
#include "test_assert.hpp"
import std;
import boost.container;

int main() {
    // pmr resource TUs (global_resource.cpp etc.)
    boost::container::pmr::memory_resource* def =
        boost::container::pmr::get_default_resource();
    assert(def != nullptr);

    boost::container::pmr::monotonic_buffer_resource mbr;
    {
        boost::container::pmr::list<int> v(&mbr);
        for (int i = 0; i < 64; ++i) v.push_back(i);
        assert(v.size() == 64 && v.back() == 63);
    }
    mbr.release();

    // header-only container surface
    boost::container::vector<int> cv;
    cv.push_back(1);
    cv.push_back(2);
    assert(cv[0] == 1 && cv[1] == 2);

    boost::container::pmr::set_default_resource(def);
    return 0;
}
