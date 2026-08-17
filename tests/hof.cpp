// boost.hof — include-only smoke (M9: public API is internal-linkage
// static constexpr objects, not module-exportable; consumers #include the
// header — import+include mixing is standard-compliant)
#include "test_assert.hpp"
#include <cassert>
#include <boost/hof.hpp>

int add1(int x) { return x + 1; }
int mul2(int x) { return x * 2; }

int main() {
    auto c = boost::hof::compose(add1, mul2);
    assert(c(5) == 11);
    assert(boost::hof::identity(7) == 7);
    assert(boost::hof::always(42)(1, 2) == 42);
    return 0;
}
