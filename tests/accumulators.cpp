// boost.accumulators smoke — accumulator set (count/mean/min/max)
// NB: the extractor objects (extract::count etc.) are const namespace-scope
// variables = internal linkage — a module cannot export them (M9 hof/units
// rule). Consumers use the extract_result<Feature> function template instead.
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
    assert(ba::extract_result<ba::tag::count>(acc) == 3u);
    assert(ba::extract_result<ba::tag::mean>(acc) == 2.0);
    assert(ba::extract_result<ba::tag::min>(acc) == 1.0);
    assert(ba::extract_result<ba::tag::max>(acc) == 3.0);
    return 0;
}
