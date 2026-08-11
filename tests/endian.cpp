// boost.endian smoke — endian types, conversion helpers
#include "test_assert.hpp"
import std;
import boost.endian;

int main() {
    boost::endian::big_uint16_t be(0x1234);
    assert(be.value() == 0x1234);
    boost::endian::little_uint32_t le(0xDEADBEEF);
    assert(le.value() == 0xDEADBEEF);
    assert(boost::endian::native_to_big(0x0102) == boost::endian::big_to_native(0x0102));
    unsigned short orig = 0xABCD;
    unsigned short rev = boost::endian::endian_reverse(orig);
    assert(rev != orig);
    assert(boost::endian::endian_reverse(rev) == orig);
    assert(boost::endian::conditional_reverse(orig,
                                              boost::endian::order::big,
                                              boost::endian::order::big) == orig);
    assert(boost::endian::conditional_reverse(orig,
                                              boost::endian::order::big,
                                              boost::endian::order::little) != orig);
    boost::endian::big_uint32_t arr[2] = {1, 2};
    assert(arr[1].value() == 2);
    return 0;
}
