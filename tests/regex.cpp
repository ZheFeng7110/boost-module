// boost.regex smoke — compiled lib linkage (match/search/replace/iterator)
#include "test_assert.hpp"
import std;
import boost.regex;

int main() {
    boost::regex re("(\\w+)@(\\w+)\\.(\\w+)");
    std::string s("user@example.com and another@host.org");
    boost::smatch m;
    assert(boost::regex_search(s, m, re));
    assert(m.size() == 4);
    assert(m[1] == "user");
    assert(m[2] == "example");
    assert(boost::regex_match(std::string("a@b.c"), re));
    assert(!boost::regex_match(std::string("not-an-email"), re));
    assert(!boost::regex_match(std::string("x@y.z"), boost::regex("\\d+")));

    std::string out = boost::regex_replace(s, re, "[$1@$2.$3]");
    assert(out == "[user@example.com] and [another@host.org]");

    int count = 0;
    for (boost::sregex_iterator it(s.begin(), s.end(), re), end; it != end; ++it)
        ++count;
    assert(count == 2);

    boost::sregex_token_iterator tok(s.begin(), s.end(), re, 1);
    boost::sregex_token_iterator tok_end;
    assert(tok != tok_end && *tok == "user");
    ++tok;
    assert(tok != tok_end && *tok == "another");
    ++tok;
    assert(tok == tok_end);

    boost::match_results<std::string::const_iterator> mr;
    assert(boost::regex_search(s, mr, re));
    assert(mr.prefix().length() == 0);
    assert(mr.suffix().str() == " and another@host.org");
    return 0;
}
