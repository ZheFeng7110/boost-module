// boost-example — consumer demo: `import boost;` aggregate module.
//
// Exercises three compiled libraries through the umbrella module:
//   - filesystem: 目录创建 / 文件读写 / 遍历
//   - json:        序列化 / 反序列化
//   - regex:       匹配 / 替换
// No `#include <boost/...>` anywhere — everything comes from the module layer.
import std;
import boost;

namespace fs = boost::filesystem;

static int failures = 0;

#define CHECK(cond)                                                             \
    do {                                                                        \
        if (!(cond)) {                                                          \
            std::printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);          \
            ++failures;                                                         \
        }                                                                       \
    } while (0)

static void demo_filesystem() {
    std::printf("== filesystem ==\n");
    fs::path dir = fs::temp_directory_path() / ("boost_example_" + std::to_string(std::clock()));
    fs::path file = dir / "note.txt";
    boost::system::error_code ec;
    CHECK(fs::create_directories(dir, ec) || fs::exists(dir, ec));
    CHECK(!ec);

    {
        fs::ofstream out(file);
        out << "hello import boost;";
        out.close();
    }
    CHECK(fs::exists(file));
    CHECK(fs::is_regular_file(file));
    CHECK(fs::file_size(file) == 19);

    {
        fs::ifstream in(file);
        std::string line;
        std::getline(in, line);
        CHECK(line == "hello import boost;");
    }

    int n = 0;
    for (fs::directory_iterator it(dir), end; it != end; ++it, ++n) {}
    CHECK(n == 1);

    fs::remove_all(dir, ec);
    CHECK(!ec);
    CHECK(!fs::exists(dir));
    std::printf("  file read/write + directory walk ok\n");
}

static void demo_json() {
    std::printf("== json ==\n");
    boost::json::value v = boost::json::parse(R"({"name":"boost","libs":["filesystem","json","regex"],"stars":42})");
    CHECK(v.is_object());
    boost::json::object& o = v.as_object();
    CHECK(o["name"].as_string() == "boost");
    CHECK(o["libs"].as_array().size() == 3);
    CHECK(o["stars"].as_int64() == 42);

    o["stars"] = 43;
    std::string ser = boost::json::serialize(v);
    CHECK(ser.find("\"stars\":43") != std::string::npos);
    CHECK(boost::json::parse(ser).as_object()["libs"].as_array()[1].as_string() == "json");
    std::printf("  serialize/parse round-trip ok: %s\n", ser.c_str());
}

static void demo_regex() {
    std::printf("== regex ==\n");
    std::string text("contact user@example.com or admin@boost.org");
    boost::regex re(R"((\w+)@(\w+)\.(\w+))");
    boost::smatch m;
    CHECK(boost::regex_search(text, m, re));
    CHECK(m.size() == 4);
    CHECK(m[1] == "user");
    CHECK(m[2] == "example");
    CHECK(m[3] == "com");

    std::string out = boost::regex_replace(text, re, "[$1@$2.$3]");
    CHECK(out == "contact [user@example.com] or [admin@boost.org]");

    int count = 0;
    for (boost::sregex_iterator it(text.begin(), text.end(), re), end; it != end; ++it)
        ++count;
    CHECK(count == 2);
    std::printf("  match/replace/iterator ok: %s\n", out.c_str());
}

int main() {
    std::printf("import boost; example - build %d\n", boost::BOOST_VERSION);
    demo_filesystem();
    demo_json();
    demo_regex();
    if (failures == 0) {
        std::printf("all examples passed\n");
        return 0;
    }
    std::printf("%d failure(s)\n", failures);
    return 1;
}
