// boost.iostreams smoke — compiled lib linkage (file_descriptor + mapped_file
// device TUs; external-library backends are out of scope, M11 doc §2)
#include "test_assert.hpp"
import std;
import boost.iostreams;

int main() {
    const std::string path = "test_iostreams.tmp";
    {
        boost::iostreams::file_descriptor_sink sink(path, std::ios_base::out);
        boost::iostreams::write(sink, "hello", 5);
    }
    {
        boost::iostreams::file_descriptor_source src(path, std::ios_base::in);
        char buf[8] = {};
        std::streamsize n = boost::iostreams::read(src, buf, sizeof(buf));
        assert(n == 5);
        assert(std::string(buf, static_cast<std::size_t>(n)) == "hello");
    }
    {
        boost::iostreams::mapped_file_source mf(path);
        assert(mf.is_open());
        assert(mf.size() == 5);
        assert(std::string(mf.data(), mf.size()) == "hello");
    }
    std::remove(path.c_str());
    return 0;
}
