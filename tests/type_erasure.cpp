// boost.type_erasure smoke — compiled lib linkage (dynamic_binding TU).
// Known limitation (M11 doc §6): the full any<> dynamic-dispatch path cannot
// be instantiated through the module face on clang-msvc — vtable.hpp's
// vtable_storage static_cast between vtable_entry<> specializations is not
// module-ODR safe. This smoke exercises the concept templates (compile-time
// face) that the module exports.
#include "test_assert.hpp"
import std;
import boost.type_erasure;

int main() {
    namespace te = boost::type_erasure;

    using inc = te::incrementable<>;
    using cp = te::copy_constructible<>;
    using vid = te::typeid_<>;
    static_assert(!std::is_same_v<inc, cp>);
    static_assert(!std::is_same_v<inc, vid>);
    return 0;
}
