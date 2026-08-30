// boost.serialization smoke — compiled lib linkage (text archive + basic
// archive TUs; the GMF carries both boost/serialization and boost/archive
// roots, M11 doc §3)
#include "test_assert.hpp"
import std;
import boost.serialization;

int main() {
    std::stringstream ss;

    {
        boost::archive::text_oarchive oa(ss);
        int v = 42;
        double d = 2.5;
        std::string s = "boost";
        oa& v;
        oa& d;
        oa& s;
    }
    {
        boost::archive::text_iarchive ia(ss);
        int v = 0;
        double d = 0;
        std::string s;
        ia& v;
        ia& d;
        ia& s;
        assert(v == 42);
        assert(d == 2.5);
        assert(s == "boost");
    }
    assert(ss.str().find("serialization::archive") != std::string::npos);
    return 0;
}
