// boost.filesystem smoke — compiled lib linkage (path/operations/directory)
#include "test_assert.hpp"
import std;
import boost.filesystem;

int main() {
    using namespace boost::filesystem;
    path p("a/b/c.txt");
    assert(p.parent_path().generic_string() == "a/b");
    assert(p.filename().string() == "c.txt");
    assert(p.extension().string() == ".txt");

    path dir = temp_directory_path() / ("boost_m4_fs_" + std::to_string(std::clock()));
    path file = dir / "hello.txt";
    boost::system::error_code ec;
    // NB: create_directories returns false when the dir already exists (repeated
    // runs reuse the same std::clock() value) — that must not skip the body.
    assert(create_directories(dir, ec) || exists(dir, ec));
    assert(!ec);
    {
        boost::filesystem::ofstream out(file);
        out << "hello boost.filesystem";
        out.close();
        assert(exists(file));
        assert(file_size(file) == 22);
        assert(is_regular_file(file));
    }
    {
        boost::filesystem::ifstream in(file);
        std::string line;
        std::getline(in, line);
        assert(line == "hello boost.filesystem");
    }
    {
        int n = 0;
        for (directory_iterator it(dir), end; it != end; ++it, ++n) {}
        assert(n == 1);
    }
    // Streams and the directory iterator above are scoped out, so no open handle
    // blocks remove_all on Windows.
    assert(remove_all(dir, ec) > 0);
    assert(!ec);
    assert(!exists(dir));
    assert(!current_path().empty());
    assert(!temp_directory_path().empty());
    assert(exists("/"));
    return 0;
}
