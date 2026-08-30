// boost.vmd — include-only smoke (M10 T3: VMD is a pure preprocessor library,
// 157 macros, no module; the import proves import+include mixing in one TU)
#include "test_assert.hpp"
import boost.config;
#include <boost/vmd/is_empty.hpp>
#include <boost/vmd/is_tuple.hpp>

#define M10_NOTHING
static_assert(BOOST_VMD_IS_EMPTY(M10_NOTHING));
static_assert(!BOOST_VMD_IS_EMPTY(1));
// VMD tuple = one parenthesized group; (a)(b) is a sequence of two tuples
static_assert(BOOST_VMD_IS_TUPLE((a, b)));
static_assert(!BOOST_VMD_IS_TUPLE((a)(b)));

int main() {
    return 0;
}
