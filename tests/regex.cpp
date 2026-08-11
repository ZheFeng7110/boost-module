// boost.regex smoke — compiled lib linkage (match/search/replace/iterator)
import std;
import boost.regex;

int main() {
    boost::regex re("(\\w+)@(\\w+)\\.(\\w+)");
    std::string s("user@example.com and another@host.org");
    boost::smatch m;
    if (!boost::regex_search(s, m, re)) return 1;
    if (m.size() != 4) return 2;
    if (m[1] != "user") return 3;
    if (m[2] != "example") return 4;
    if (!boost::regex_match(std::string("a@b.c"), re)) return 5;
    if (boost::regex_match(std::string("not-an-email"), re)) return 6;
    if (boost::regex_match(std::string("x@y.z"), boost::regex("\\d+"))) return 7;

    std::string out = boost::regex_replace(s, re, "[$1@$2.$3]");
    if (out != "[user@example.com] and [another@host.org]") return 8;

    int count = 0;
    for (boost::sregex_iterator it(s.begin(), s.end(), re), end; it != end; ++it)
        ++count;
    if (count != 2) return 9;

    boost::sregex_token_iterator tok(s.begin(), s.end(), re, 1);
    boost::sregex_token_iterator tok_end;
    if (tok == tok_end || *tok != "user") return 10;
    ++tok;
    if (tok == tok_end || *tok != "another") return 11;
    ++tok;
    if (tok != tok_end) return 12;

    boost::match_results<std::string::const_iterator> mr;
    if (!boost::regex_search(s, mr, re)) return 13;
    if (mr.prefix().length() != 0) return 14;
    if (mr.suffix().str() != " and another@host.org") return 15;
    return 0;
}
