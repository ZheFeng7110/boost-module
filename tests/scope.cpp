// boost.scope smoke — scope_exit / scope_fail / scope_success / unique_resource
#include "test_assert.hpp"
import std;
import boost.scope;

int main() {
    int v = 0;
    {
        auto g = boost::scope::make_scope_exit([&v] { v += 10; });
        ++v;
    }
    assert(v == 11);
    {
        auto g = boost::scope::make_scope_success([&v] { v += 100; });
        ++v;
    }
    assert(v == 112);
    try {
        auto g = boost::scope::make_scope_fail([&v] { v += 1000; });
        ++v;
        throw 1;
    } catch (...) {
    }
    assert(v == 1113);
    {
        auto g = boost::scope::make_scope_success([&v] { v += 10000; });
        try {
            throw 1;
        } catch (...) {
        }
    }
    assert(v == 11113);
    try {
        auto g = boost::scope::make_scope_fail([&v] { v += 100000; });
        ++v;
        throw 2;
    } catch (...) {
    }
    assert(v == 111114);
    boost::scope::unique_resource<int, void(*)(int)> ur(3, [](int) {});
    assert(ur.get() == 3);
    boost::scope::make_unique_resource_checked(-1, -1, [](int) {});
    return 0;
}
