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
    if (create_directories(dir, ec)) {
        boost::filesystem::ofstream out(file);
        out << "hello boost.filesystem";
        out.close();
        assert(exists(file));
        assert(file_size(file) == 21);
        assert(is_regular_file(file));
        boost::filesystem::ifstream in(file);
        std::string line;
        std::getline(in, line);
        assert(line == "hello boost.filesystem");
        int n = 0;
        for (directory_iterator it(dir), end; it != end; ++it, ++n) {}
        assert(n == 1);
        remove_all(dir, ec);
        assert(!ec);
        assert(!exists(dir));
    }
    assert(!current_path().empty());
    assert(!temp_directory_path().empty());
    assert(exists("/"));
    return 0;
}
