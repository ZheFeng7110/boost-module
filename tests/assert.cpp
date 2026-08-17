// boost.assert smoke — source_location entity (BOOST_ASSERT macros are
// include-only; this TU uses the module's exported source_location type)
#include "test_assert.hpp"
import std;
import boost.assert;

int main() {
    boost::source_location loc;
    assert(loc.line() == 0);
    return 0;
}
