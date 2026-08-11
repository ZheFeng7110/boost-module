// boost.url smoke — compiled lib linkage (parse/components/encode/decode)
import std;
import boost.url;
import boost.system;

int main() {
    namespace urls = boost::urls;

    urls::result<urls::url> r = urls::parse_uri(
        "https://user:pass@example.com:8443/path/to/file.html?k=v&q=1#frag");
    if (!r) return 1;
    urls::url u = *r;
    if (u.scheme() != "https") return 2;
    if (u.host() != "example.com") return 3;
    if (u.port() != "8443") return 4;
    if (u.port_number() != 8443) return 5;
    if (u.userinfo() != "user:pass") return 6;
    if (u.path() != "/path/to/file.html") return 7;
    if (u.encoded_query() != "k=v&q=1") return 8;
    if (u.fragment() != "frag") return 9;
    if (u.encoded_fragment() != "frag") return 10;
    if (u.query().empty()) return 11;
    if (u.query() != "k=v&q=1") return 12;
    auto p0 = u.params().begin();
    if ((*p0).key != "k") return 13;
    auto p1 = std::next(p0);
    if ((*p1).value != "1") return 14;

    urls::result<urls::url> rr = urls::parse_uri_reference("/relative/path");
    if (!rr) return 15;
    if (rr->path() != "/relative/path") return 16;

    urls::url u2 = urls::url();
    u2.set_scheme("http");
    u2.set_host("localhost");
    u2.set_path("/a b");
    if (u2.encoded_path() != "/a%20b") return 17;
    if (u2.path() != "/a b") return 18;

    urls::pct_string_view ps;
    urls::result<urls::pct_string_view> psr =
        urls::make_pct_string_view("a%20b");
    if (!psr) return 19;
    if (psr->decode() != "a b") return 20;

    urls::result<urls::ipv4_address> ip = urls::parse_ipv4_address("192.168.0.1");
    if (!ip) return 21;
    if (ip->to_string() != "192.168.0.1") return 22;

    std::string enc = urls::encode(
        "a b/c", urls::grammar::lut_chars("abc "), urls::encoding_opts{}, urls::string_token::return_string{});
    if (enc != "a b%2Fc") return 23;
    return 0;
}
