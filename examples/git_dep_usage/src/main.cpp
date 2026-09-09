// boost-example-git-dep — consumer demo: git dep + selective features.
//
// The manifest closes default features off and opts in to exactly three
// libraries (optional / json / version), so only those module interfaces are
// built — `import boost;` re-exports precisely the activated set (empty
// closures are also legal, but here it is non-empty).
// No `#include <boost/...>` anywhere — everything comes from the module layer.
import std;
import boost;

static int failures = 0;

#define CHECK(cond)                                                             \
    do {                                                                        \
        if (!(cond)) {                                                          \
            std::printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond);          \
            ++failures;                                                         \
        }                                                                       \
    } while (0)

static void demo_optional() {
    std::printf("== optional ==\n");
    boost::optional<int> empty;
    CHECK(!empty.has_value());

    boost::optional<int> v(42);
    CHECK(v.has_value());
    CHECK(*v == 42);
    CHECK(v.value_or(0) == 42);

    empty = 7;
    CHECK(empty.value_or(0) == 7);
    std::printf("  has_value/value_or ok\n");
}

static void demo_json() {
    std::printf("== json ==\n");
    boost::json::value v = boost::json::parse(R"({"name":"git-dep","features":["optional","json","version"]})");
    CHECK(v.is_object());
    boost::json::object& o = v.as_object();
    CHECK(o["name"].as_string() == "git-dep");
    CHECK(o["features"].as_array().size() == 3);

    o["name"] = "selected-features";
    std::string ser = boost::json::serialize(v);
    CHECK(ser.find("\"name\":\"selected-features\"") != std::string::npos);
    CHECK(boost::json::parse(ser).as_object()["features"].as_array()[0].as_string() == "optional");
    std::printf("  serialize/parse round-trip ok: %s\n", ser.c_str());
}

static void demo_version() {
    std::printf("== version ==\n");
    CHECK(boost::BOOST_VERSION == 109100);
    CHECK(boost::BOOST_LIB_VERSION[0] == '1');
    std::printf("  BOOST_VERSION = %d\n", boost::BOOST_VERSION);
}

int main() {
    std::printf("git-dep example - build %d\n", boost::BOOST_VERSION);
    demo_optional();
    demo_json();
    demo_version();
    if (failures == 0) {
        std::printf("all examples passed\n");
        return 0;
    }
    std::printf("%d failure(s)\n", failures);
    return 1;
}
