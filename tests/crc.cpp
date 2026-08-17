// boost.crc smoke — CRC computation
#include "test_assert.hpp"
import std;
import boost.crc;

int main() {
    boost::crc_32_type crc;
    crc.process_bytes("123456789", 9);
    assert(crc.checksum() == 0xCBF43926u);
    boost::crc_16_type crc16;
    crc16.process_bytes("123456789", 9);
    assert(crc16.checksum() == 0xBB3Du);
    boost::crc_optimal<16, 0x1021, 0xFFFF, 0, false, false> custom;
    custom.process_bytes("123456789", 9);
    assert(custom.checksum() != 0);
    const void* data = "123456789";
    assert((boost::augmented_crc<32, 0x04C11DB7u>(data, 9u) != 0));
    return 0;
}
