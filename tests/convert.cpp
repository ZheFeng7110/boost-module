// boost.convert smoke — string-to-int conversion via cstring converter
#include "test_assert.hpp"
import std;
import boost.convert;

int main() {
    struct int_cnv {
        bool operator()(std::string_view v, boost::optional<int>& r) const {
            try {
                std::size_t pos = 0;
                int n = std::stoi(std::string(v), &pos);
                if (pos != v.size()) return false;
                r = n;
                return true;
            } catch (...) {
                return false;
            }
        }
    };
    int_cnv cnv;
    boost::optional<int> r = boost::convert<int>("42", cnv);
    assert(r.has_value() && *r == 42);
    boost::optional<int> bad = boost::convert<int>("abc", cnv);
    assert(!bad.has_value());
    return 0;
}
