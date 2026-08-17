// boost.winapi smoke — Windows API surface types/functions (declarations
// compile everywhere; functions link on Windows only)
#include "test_assert.hpp"
import std;
import boost.winapi;

int main() {
    boost::winapi::DWORD_ d = 0;
    boost::winapi::BOOL_ b = 1;
    assert(b == 1);
    boost::winapi::HANDLE_ h = nullptr;
    assert(h == nullptr);
#if defined(_WIN32)
    assert(boost::winapi::GetCurrentProcessId != nullptr);
#endif
    (void)d;
    return 0;
}
