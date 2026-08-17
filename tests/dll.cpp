// boost.dll smoke — shared_library default state only (path conversion on
// the MSVC flavor crashes in program_location — upstream issue, see M9 doc)
#include "test_assert.hpp"
import std;
import boost.dll;

int main() {
    boost::dll::shared_library lib;
    assert(!lib.is_loaded());
    assert(!lib);
    return 0;
}
