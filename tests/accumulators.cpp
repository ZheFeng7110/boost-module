// boost.accumulators smoke — accumulator set (count/mean/min/max)
// The extractor objects (extract::count etc.) are namespace-scope const
// variables; the vendored `inline` patch gives them external linkage, so the
// whole extract::* / boost::accumulators::* object face now exports through
// the module (no more extract_result<> workaround required).
#include "test_assert.hpp"
import std;
import boost.accumulators;

int main() {
    namespace ba = boost::accumulators;
    ba::accumulator_set<double, ba::features<ba::tag::count, ba::tag::mean,
                                              ba::tag::min, ba::tag::max>> acc;
    acc(1.0);
    acc(2.0);
    acc(3.0);
    assert(ba::extract::count(acc) == 3u);
    assert(ba::extract::mean(acc) == 2.0);
    assert(ba::extract::min(acc) == 1.0);
    assert(ba::extract::max(acc) == 3.0);
    // The `using extract::mean;` injection at boost::accumulators scope is
    // exportable too once the target has external linkage.
    assert(ba::mean(acc) == 2.0);
    return 0;
}
