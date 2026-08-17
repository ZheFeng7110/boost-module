// boost.format smoke — printf-style formatting
#include "test_assert.hpp"
import std;
import boost.format;

int main() {
    boost::format f("%1% + %2% = %3%");
    f % 1 % 2 % 3;
    assert(f.str() == "1 + 2 = 3");
    std::string s = boost::str(boost::format("%05d") % 42);
    assert(s == "00042");
    assert(boost::str(boost::format("%2$.1f %1$s") % "x" % 3.14) == "3.1 x");
    assert(boost::str(boost::format("%|10|") % "hi") == "        hi");
    boost::format ff("%1% %1%");
    ff % 7;
    assert(ff.str() == "7 7");
    bool caught = false;
    try {
        boost::format bad("%1% %2%");
        bad % 1;
        bad.str();
    } catch (boost::io::bad_format_string const&) {
        caught = true;
    } catch (boost::io::too_few_args const&) {
        caught = true;
    } catch (...) {
    }
    assert(caught);
    return 0;
}
