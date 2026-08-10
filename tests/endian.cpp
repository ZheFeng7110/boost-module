// boost.endian smoke — endian types, conversion helpers
import std;
import boost.endian;

int main() {
    boost::endian::big_uint16_t be(0x1234);
    if (be.value() != 0x1234) return 1;
    boost::endian::little_uint32_t le(0xDEADBEEF);
    if (le.value() != 0xDEADBEEF) return 2;
    if (boost::endian::native_to_big(0x0102) != boost::endian::big_to_native(0x0102)) return 3;
    unsigned short orig = 0xABCD;
    unsigned short rev = boost::endian::endian_reverse(orig);
    if (rev == orig) return 4;
    if (boost::endian::endian_reverse(rev) != orig) return 5;
    if (boost::endian::conditional_reverse(orig,
                                           boost::endian::order::big,
                                           boost::endian::order::big) != orig) return 6;
    if (boost::endian::conditional_reverse(orig,
                                           boost::endian::order::big,
                                           boost::endian::order::little) == orig) return 7;
    boost::endian::big_uint32_t arr[2] = {1, 2};
    if (arr[1].value() != 2) return 8;
    return 0;
}
