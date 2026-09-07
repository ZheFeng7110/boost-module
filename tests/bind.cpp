// boost.bind smoke — C4 re-modularization (2026-09-07): the M10 T3
// "macro-driven" attribution was wrong — all 9 BOOST_BIND_* macros are
// implementation details (include guard, call-convention config, X-macro
// helpers); the API is the boost::bind function template + boost::arg<I> +
// boost::placeholders::_1.._9 (BOOST_INLINE_CONSTEXPR, external linkage).
// The deprecated boost/bind.hpp global `using namespace
// boost::placeholders;` is include-face-only (a module cannot inject a
// using-directive into the consumer's global namespace) — module consumers
// qualify or use-declare the placeholders themselves (upstream-recommended
// spelling).
#include <cassert>
#include <functional>
#include <string>
import boost.bind;

int main() {
    auto add = boost::bind(std::plus<int>(), boost::placeholders::_1,
                           boost::placeholders::_2);
    assert(add(2, 3) == 5);
    int v = 7;
    auto bound = boost::bind(std::plus<int>(), boost::ref(v),
                             boost::placeholders::_1);
    assert(bound(35) == 42);
    boost::arg<1> a1 = boost::placeholders::_1;
    (void)a1;
    auto mem = boost::mem_fn(&std::string::size);
    assert(mem(std::string("abcd")) == 4u);
    return 0;
}
