// boost.beast smoke — flat_buffer + http request/response types (no sockets)
#include "test_assert.hpp"
import std;
import boost.beast;

int main() {
    namespace beast = boost::beast;
    namespace http = beast::http;

    beast::flat_buffer buf;
    assert(buf.size() == 0);

    http::request<http::string_body> req{http::verb::get, "/index.html", 11};
    req.set(http::field::host, "example.com");
    req.set(http::field::user_agent, "boost-module-test");
    assert(req.method() == http::verb::get);
    assert(req.target() == "/index.html");
    assert(req.version() == 11);
    assert(req[http::field::host] == "example.com");

    http::response<http::string_body> res{http::status::ok, 11};
    res.body() = "hello";
    assert(res.result() == http::status::ok);
    assert(res.body() == "hello");
    return 0;
}
