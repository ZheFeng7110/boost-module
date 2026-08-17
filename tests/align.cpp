// boost.align smoke — align/align_up/align_down, alignment_of, is_aligned
#include "test_assert.hpp"
import std;
import boost.align;

int main() {
    unsigned char buf[64];
    void* p = buf + 3;
    std::size_t space = sizeof(buf) - 3;
    assert(!boost::alignment::is_aligned(p, 8));
    void* r = boost::alignment::align(8, 4, p, space);
    assert(r != nullptr);
    assert(boost::alignment::is_aligned(p, 8));
    assert(space >= 4);
    assert(boost::alignment::align_up<std::size_t>(13, 8) == 16);
    assert(boost::alignment::align_down<std::size_t>(13, 8) == 8);
    assert(boost::alignment::alignment_of<double>::value >= 4);
    assert(boost::alignment::is_aligned(buf + 8, 8));
    return 0;
}
