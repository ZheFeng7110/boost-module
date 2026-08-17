// boost.type_index smoke — runtime type identification
#include "test_assert.hpp"
import std;
import boost.type_index;

int main() {
    auto t1 = boost::typeindex::type_id<int>();
    auto t2 = boost::typeindex::type_id<int>();
    auto t3 = boost::typeindex::type_id<double>();
    assert(t1 == t2);
    assert(t1 != t3);
    assert(t1.pretty_name() == t2.pretty_name());
    int x = 5;
    auto rt = boost::typeindex::type_id_runtime(x);
    assert(rt == t1);
    std::string s = "s";
    assert(boost::typeindex::type_id<std::string>() == boost::typeindex::type_id_runtime(s));
    assert(t1.hash_code() == t2.hash_code());
    return 0;
}
