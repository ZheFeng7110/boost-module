// boost.uuid smoke — uuid generation and comparison
#include "test_assert.hpp"
import std;
import boost.uuid;

int main() {
    boost::uuids::uuid u;
    assert(u.is_nil());
    assert(boost::uuids::uuid{} == u);
    boost::uuids::string_generator gen;
    boost::uuids::uuid v = gen("01234567-89ab-cdef-0123-456789abcdef");
    assert(!v.is_nil());
    assert(v != u);
    boost::uuids::uuid v2 = gen("01234567-89ab-cdef-0123-456789abcdef");
    assert(v == v2);
    boost::uuids::random_generator rng;
    boost::uuids::uuid r1 = rng();
    boost::uuids::uuid r2 = rng();
    assert(!r1.is_nil() && !r2.is_nil());
    assert(r1 != r2);
    assert(v.size() == 16);
    return 0;
}
