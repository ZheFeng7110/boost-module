// boost.proto — include-only smoke (M10 T3: the EDSL face is the
// BOOST_PROTO_* macro family + expression templates, no module; the import
// proves import+include mixing in one TU)
#include "test_assert.hpp"
#include <type_traits>
import boost.config;
#include <boost/proto/core.hpp>
#include <boost/proto/literal.hpp>

int main() {
    boost::proto::terminal<int>::type t = {42};
    assert(boost::proto::value(t) == 42);

    boost::proto::terminal<boost::proto::_>::type _;
    (void)_;

    auto expr = boost::proto::lit(1) + 2;
    static_assert(boost::proto::arity_of<decltype(expr)>::value == 2);
    assert(boost::proto::value(boost::proto::child_c<0>(expr)) == 1);
    return 0;
}
