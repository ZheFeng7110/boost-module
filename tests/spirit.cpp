// boost.spirit — include-only smoke (M10 T3: the parser-building face is the
// BOOST_SPIRIT_* macro family + the qi grammar API, no module; the import
// proves import+include mixing in one TU)
#include "test_assert.hpp"
#include <string>
import boost.config;
#include <boost/spirit/include/qi.hpp>

namespace qi = boost::spirit::qi;

int main() {
    std::string const input = "42";
    int value = 0;
    bool ok = qi::parse(input.begin(), input.end(), qi::int_, value);
    assert(ok && value == 42);
    return 0;
}
