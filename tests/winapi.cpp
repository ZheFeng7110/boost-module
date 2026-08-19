// boost.winapi smoke — Windows API surface types/functions (declarations
// compile everywhere; functions link on Windows only)
#include "test_assert.hpp"
import std;
import boost.winapi;

int main() {
#if defined(_WIN32) || defined(__CYGWIN__)
    boost::winapi::DWORD_ d = 0;
    boost::winapi::BOOL_ b = 1;
    assert(b == 1);
    boost::winapi::HANDLE_ h = nullptr;
    assert(h == nullptr);
    assert(boost::winapi::GetCurrentProcessId != nullptr);
    (void)d;
#else
    // winapi module is empty on POSIX (basic_types.hpp #errors off-Windows);
    // the module exists only so system/thread/dll/icl/flyweight can
    // `export import boost.winapi;` on every platform.
#endif
    return 0;
}
