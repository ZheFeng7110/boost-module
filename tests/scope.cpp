// boost.scope smoke — scope_exit / scope_fail / scope_success / unique_resource
import std;
import boost.scope;

int main() {
    int v = 0;
    {
        auto g = boost::scope::make_scope_exit([&v] { v += 10; });
        ++v;
    }
    if (v != 11) return 1;
    {
        auto g = boost::scope::make_scope_success([&v] { v += 100; });
        ++v;
    }
    if (v != 112) return 2;
    try {
        auto g = boost::scope::make_scope_fail([&v] { v += 1000; });
        ++v;
        throw 1;
    } catch (...) {
    }
    if (v != 1113) return 3;
    {
        auto g = boost::scope::make_scope_success([&v] { v += 10000; });
        try {
            throw 1;
        } catch (...) {
        }
    }
    if (v != 11113) return 4;
    try {
        auto g = boost::scope::make_scope_fail([&v] { v += 100000; });
        ++v;
        throw 2;
    } catch (...) {
    }
    if (v != 111114) return 5;
    boost::scope::unique_resource<int, void(*)(int)> ur(3, [](int) {});
    if (ur.get() != 3) return 6;
    boost::scope::make_unique_resource_checked(-1, -1, [](int) {});
    return 0;
}
