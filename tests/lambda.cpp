// boost.lambda smoke — C4 re-modularization (2026-09-07): classic lambda's
// placeholders _1.._3 (core.hpp) and _e (exceptions.hpp) were TU-local
// (anonymous-namespace objects, internal linkage) — the real reason the
// library sat in the M10 include-only list, not its (tiny, all-internal)
// macro face. C4 vendored patches convert them to `inline constexpr`
// (external linkage, cross-TU merging — hof/units C2 treatment; the
// lambda_functor default constructor became constexpr), so they export
// through the boost.lambda module face. Macro/API template consumption
// (BOOST_LAMBDA_*-style user-side code has none; the API is functor
// templates) works through the module; include-face consumption stays
// available unchanged.
#include "test_assert.hpp"
#include <algorithm>
#include <cassert>
import boost.lambda;

int main() {
    int arr[3] = {1, 2, 3};
    std::for_each(arr, arr + 3, boost::lambda::_1 += 10);
    assert(arr[0] == 11 && arr[1] == 12 && arr[2] == 13);
    std::for_each(arr, arr + 3,
                  boost::lambda::if_(boost::lambda::_1 > 11)
                      [boost::lambda::_1 = 0]);
    assert(arr[0] == 11 && arr[1] == 0 && arr[2] == 0);
    auto c = boost::lambda::bind(std::plus<int>(), boost::lambda::_1,
                                 boost::lambda::_2);
    assert(c(2, 3) == 5);
    // _e: exception placeholder in a try/catch lambda expression
    int caught = 0;
    try {
        boost::lambda::try_catch(
            boost::lambda::throw_exception(42),
            boost::lambda::catch_exception<int>(
                boost::lambda::var(caught) = 1))();
    } catch (...) {
        caught = 2;
    }
    assert(caught == 1);
    return 0;
}
