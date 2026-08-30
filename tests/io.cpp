// boost.io smoke — quoted, ostream_joiner, saver types. ostream_put is
// include-side (curated out of the module GMF, M11: gcc 16.1 buffer_fill
// enum mismatch); the rest comes from the module. The include sits before
// the imports so the TU's own STL definitions load first (M9 §4 pattern).
#include "test_assert.hpp"
#include <boost/io/ostream_put.hpp>
import std;
import boost.io;

int main() {
    std::ostringstream os;
    os << boost::io::quoted(std::string("a \"b\" c"));
    assert(os.str() == "\"a \\\"b\\\" c\"");
    std::istringstream is("\"quoted value\" rest");
    std::string s;
    is >> boost::io::quoted(s);
    assert(s == "quoted value");
    {
        boost::io::ios_flags_saver saver(os);
        os.setf(std::ios::hex, std::ios::basefield);
        os << 15;
    }
    assert(os.str().back() == 'f');
    os.str("");
    os.clear();
    std::vector<int> v{1, 2, 3};
    auto joiner = boost::io::make_ostream_joiner(os, ",");
    std::copy(v.begin(), v.end(), joiner);
    assert(os.str() == "1,2,3");
    os.str("");
    boost::io::ostream_put(os, "xy", 2);
    assert(os.str() == "xy");
    return 0;
}
