// boost.xpressive — include-only smoke (M10 T3: the regex EDSL face is the
// BOOST_XPRESSIVE_* macro family + expression templates, no module; the
// import proves import+include mixing in one TU)
#include "test_assert.hpp"
#include <string>
import boost.config;
#include <boost/xpressive/xpressive.hpp>

namespace xp = boost::xpressive;

int main() {
    std::string s = "hello 42";
    xp::sregex re = xp::_d >> +xp::_d;  // one-or-more digits
    xp::smatch m;
    bool ok = xp::regex_search(s, m, re);
    assert(ok && m[0].str() == "42");
    return 0;
}
