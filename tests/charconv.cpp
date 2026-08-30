// boost.charconv smoke — compiled lib linkage (from_chars/to_chars TUs)
#include "test_assert.hpp"
import std;
import boost.charconv;

int main() {
    char buf[64] = {};

    auto ri = boost::charconv::to_chars(buf, buf + sizeof(buf), 12345);
    assert(ri.ec == std::errc());
    int iv = 0;
    auto rri = boost::charconv::from_chars(buf, ri.ptr, iv);
    assert(rri.ec == std::errc() && iv == 12345);

    auto rd = boost::charconv::to_chars(buf, buf + sizeof(buf), 3.25);
    assert(rd.ec == std::errc());
    double dv = 0;
    auto rrd = boost::charconv::from_chars(buf, rd.ptr, dv);
    assert(rrd.ec == std::errc() && dv == 3.25);

    // negative + integer round-trip via from_chars payload
    auto rn = boost::charconv::to_chars(buf, buf + sizeof(buf), -7);
    assert(rn.ec == std::errc());
    int nv = 0;
    assert(boost::charconv::from_chars(buf, rn.ptr, nv).ec == std::errc());
    assert(nv == -7);
    return 0;
}
