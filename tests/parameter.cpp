// boost.parameter — include-only smoke (M10 T3: BOOST_PARAMETER_* macro face
// (1.1k macros) generates the named-parameter plumbing, no module; the import
// proves import+include mixing in one TU)
#include "test_assert.hpp"
import boost.config;
#include <boost/parameter.hpp>

// BOOST_PARAMETER_NAME(index) generates tag::index + keyword _index (leading
// underscore, upstream convention); inside the function body `index` is the
// argument value.
BOOST_PARAMETER_NAME(index)

BOOST_PARAMETER_FUNCTION((int), get_index, tag, (required (index, *)))
{
    return index;
}

int main() {
    assert(get_index(_index = 42) == 42);
    return 0;
}
