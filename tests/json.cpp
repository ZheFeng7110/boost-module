// boost.json smoke — compiled lib linkage (parse/serialize/error)
import std;
import boost.json;
import boost.system;

int main() {
    boost::json::value v = boost::json::parse(R"({"a":1,"b":[10,20,30],"c":"x"})");
    if (!v.is_object()) return 1;
    boost::json::object& o = v.as_object();
    if (o["a"].as_int64() != 1) return 2;
    if (o["b"].as_array().size() != 3) return 3;
    if (o["b"].as_array()[1].as_int64() != 20) return 4;
    if (o["c"].as_string() != "x") return 5;

    boost::json::value w = boost::json::parse("42");
    if (w.as_int64() != 42) return 6;
    boost::json::value b = boost::json::parse("true");
    if (!b.as_bool()) return 7;

    std::string ser = boost::json::serialize(v);
    if (ser.find("\"a\":1") == std::string::npos) return 8;

    boost::json::array arr;
    arr.push_back(1);
    arr.push_back(2.5);
    arr.push_back("s");
    if (arr.size() != 3) return 9;

    boost::json::object obj;
    obj.emplace("k", arr);
    if (obj["k"].as_array().size() != 3) return 10;

    boost::system::error_code ec;
    boost::json::value bad = boost::json::parse("{invalid", ec);
    if (!ec) return 11;
    if (!bad.is_null()) return 12;

    boost::json::value nul;
    if (!nul.is_null()) return 13;

    boost::json::value pi = boost::json::parse("3.25");
    if (pi.as_double() != 3.25) return 14;
    return 0;
}
