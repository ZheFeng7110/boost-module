// boost.nowide smoke — compiled lib linkage (stdio/filebuf/iostream TUs)
#include "test_assert.hpp"
import std;
import boost.nowide;

int main() {
    const std::string path = "test_nowide.tmp";
    {
        boost::nowide::ofstream out(path);
        assert(out.is_open());
        out << "hello nowide" << std::endl;
    }
    {
        boost::nowide::ifstream in(path);
        assert(in.is_open());
        std::string word;
        in >> word;
        assert(word == "hello");
        in >> word;
        assert(word == "nowide");
    }

    // UTF-8 <-> UTF-16 conversion (conversion is header-side, stdio TUs above)
    std::wstring wide = boost::nowide::widen("ascii");
    assert(wide == L"ascii");
    std::string narrow = boost::nowide::narrow(wide);
    assert(narrow == "ascii");

    std::remove(path.c_str());
    return 0;
}
