// boost.url smoke — compiled lib linkage (parse/components/encode/decode)
#include "test_assert.hpp"
import std;
import boost.url;
import boost.system;

int main() {
    namespace urls = boost::urls;

    urls::result<urls::url> r = urls::parse_uri(
        "https://user:pass@example.com:8443/path/to/file.html?k=v&q=1#frag");
    assert(r);
    urls::url u = *r;
    assert(u.scheme() == "https");
    assert(u.host() == "example.com");
    assert(u.port() == "8443");
    assert(u.port_number() == 8443);
    assert(u.userinfo() == "user:pass");
    assert(u.path() == "/path/to/file.html");
    assert(u.encoded_query() == "k=v&q=1");
    assert(u.fragment() == "frag");
    assert(u.encoded_fragment() == "frag");
    assert(!u.query().empty());
    assert(u.query() == "k=v&q=1");
    auto p0 = u.params().begin();
    assert((*p0).key == "k");
    auto p1 = std::next(p0);
    assert((*p1).value == "1");

    urls::result<urls::url> rr = urls::parse_uri_reference("/relative/path");
    assert(rr);
    assert(rr->path() == "/relative/path");

    urls::url u2 = urls::url();
    u2.set_scheme("http");
    u2.set_host("localhost");
    u2.set_path("/a b");
    assert(u2.encoded_path() == "/a%20b");
    assert(u2.path() == "/a b");

    urls::pct_string_view ps;
    urls::result<urls::pct_string_view> psr =
        urls::make_pct_string_view("a%20b");
    assert(psr);
    assert(psr->decode() == "a b");

    urls::result<urls::ipv4_address> ip = urls::parse_ipv4_address("192.168.0.1");
    assert(ip);
    assert(ip->to_string() == "192.168.0.1");

    std::string enc = urls::encode(
        "a b/c", urls::grammar::lut_chars("abc "), urls::encoding_opts{}, urls::string_token::return_string{});
    assert(enc == "a b%2Fc");
    return 0;
}
