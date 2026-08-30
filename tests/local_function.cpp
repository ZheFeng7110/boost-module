// boost.local_function — include-only smoke (M10 T3: BOOST_LOCAL_FUNCTION_*
// macro face generates local function objects, no module; the import proves
// import+include mixing in one TU)
#include "test_assert.hpp"
import boost.config;
#include <boost/local_function.hpp>

int main() {
    int factor = 2;
    int BOOST_LOCAL_FUNCTION(int x, const bind factor)
    {
        return x * factor;
    }
    BOOST_LOCAL_FUNCTION_NAME(times_factor)
    assert(times_factor(21) == 42);
    return 0;
}
