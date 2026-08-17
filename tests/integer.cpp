// boost.integer smoke — integer type selection, gcd/lcm, integer_traits
#include "test_assert.hpp"
import std;
import boost.integer;

int main() {
    static_assert(sizeof(boost::int_t<32>::least) >= 4);
    static_assert(sizeof(boost::uint_t<16>::least) >= 2);
    static_assert(std::is_signed<boost::int_fast_t<int>::fast>::value);
    assert(boost::integer::gcd(12, 18) == 6);
    assert(boost::integer::gcd(7, 13) == 1);
    assert(boost::integer::lcm(4, 6) == 12);
    assert(boost::integer_log2(16u) == 4);
    assert(boost::integer_traits<int>::const_max == std::numeric_limits<int>::max());
    assert(boost::high_bit_mask_t<3>::high_bit == 8);
    assert(boost::low_bits_mask_t<3>::sig_bits == 7);
    return 0;
}
