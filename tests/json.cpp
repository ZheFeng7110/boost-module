// boost.json smoke — compiled lib linkage (parse/serialize/error)
#include "test_assert.hpp"
import std;
import boost.json;
import boost.system;

int main() {
    boost::json::value v = boost::json::parse(R"({"a":1,"b":[10,20,30],"c":"x"})");
    assert(v.is_object());
    boost::json::object& o = v.as_object();
    assert(o["a"].as_int64() == 1);
    assert(o["b"].as_array().size() == 3);
    assert(o["b"].as_array()[1].as_int64() == 20);
    assert(o["c"].as_string() == "x");

    boost::json::value w = boost::json::parse("42");
    assert(w.as_int64() == 42);
    boost::json::value b = boost::json::parse("true");
    assert(b.as_bool());

    std::string ser = boost::json::serialize(v);
    assert(ser.find("\"a\":1") != std::string::npos);

    boost::json::array arr;
    arr.push_back(1);
    arr.push_back(2.5);
    arr.push_back("s");
    assert(arr.size() == 3);

    boost::json::object obj;
    obj.emplace("k", arr);
    assert(obj["k"].as_array().size() == 3);

    boost::system::error_code ec;
    boost::json::value bad = boost::json::parse("{invalid", ec);
    assert(ec);
    assert(bad.is_null());

    boost::json::value nul;
    assert(nul.is_null());

    boost::json::value pi = boost::json::parse("3.25");
    assert(pi.as_double() == 3.25);
    return 0;
}
