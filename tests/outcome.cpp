// boost.outcome smoke — result/outcome error handling
#include "test_assert.hpp"
import std;
import boost.outcome;

int main() {
    namespace o = boost::outcome_v2;
    o::result<int> r1 = 5;
    assert(r1.has_value() && r1.value() == 5);
    o::result<int> r2 = o::failure(std::make_error_code(std::errc::invalid_argument));
    assert(!r2.has_value() && r2.has_error());
    assert(r2.error() == std::errc::invalid_argument);
    o::result<int> r3 = o::success(7);
    assert(r3.value() == 7);
    o::outcome<int, std::error_code, std::string> oc = 9;
    assert(oc.has_value() && oc.value() == 9);
    o::result<void> e = o::success();
    assert(e.has_value());
    return 0;
}
