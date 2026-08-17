// boost.config smoke — config module entities (int128 + long_long typedefs;
// the int128 entities are guarded per-platform)
#include "test_assert.hpp"
import std;
import boost.config;

int main() {
    boost::long_long_type ll = 42;
    boost::ulong_long_type ull = 84;
    assert(ll == 42 && ull == 84);
    static_assert(sizeof(boost::long_long_type) >= 8);
#if defined(BOOST_HAS_INT128)
    boost::int128_type i128 = 1;
    boost::uint128_type u128 = 2;
    assert(i128 == 1 && u128 == 2);
#endif
    return 0;
}
