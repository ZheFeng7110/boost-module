// boost.filesystem smoke — compiled lib linkage (path/operations/directory)
import std;
import boost.filesystem;

int main() {
    using namespace boost::filesystem;
    path p("a/b/c.txt");
    if (p.parent_path().generic_string() != "a/b") return 1;
    if (p.filename().string() != "c.txt") return 2;
    if (p.extension().string() != ".txt") return 3;

    path dir = temp_directory_path() / ("boost_m4_fs_" + std::to_string(std::clock()));
    path file = dir / "hello.txt";
    boost::system::error_code ec;
    if (create_directories(dir, ec)) {
        boost::filesystem::ofstream out(file);
        out << "hello boost.filesystem";
        out.close();
        if (!exists(file)) return 4;
        if (file_size(file) != 21) return 5;
        if (!is_regular_file(file)) return 6;
        boost::filesystem::ifstream in(file);
        std::string line;
        std::getline(in, line);
        if (line != "hello boost.filesystem") return 7;
        int n = 0;
        for (directory_iterator it(dir), end; it != end; ++it, ++n) {}
        if (n != 1) return 8;
        remove_all(dir, ec);
        if (ec) return 9;
        if (exists(dir)) return 10;
    }
    if (current_path().empty()) return 11;
    if (temp_directory_path().empty()) return 12;
    if (!exists("/")) return 13;
    return 0;
}
