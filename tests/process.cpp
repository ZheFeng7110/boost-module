// boost.process smoke — v2 API; compiled lib linkage (pid / environment /
// detail TUs)
#include "test_assert.hpp"
import std;
import boost.process;

int main() {
    namespace v2 = boost::process::v2;

    // pid TU symbol (current_pid lives in src/pid.cpp)
    v2::pid_type self = v2::current_pid();
    assert(self != 0);
    assert(v2::parent_pid(self) != self);

    // environment detail TUs + header-side lookups
    auto path = v2::environment::get("PATH");
    assert(!path.empty());
    return 0;
}
