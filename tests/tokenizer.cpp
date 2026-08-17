// boost.tokenizer smoke — tokenizer with separators
#include "test_assert.hpp"
import std;
import boost.tokenizer;

int main() {
    std::string s = "foo,bar,baz";
    boost::tokenizer<boost::char_separator<char>> tok(s, boost::char_separator<char>(","));
    std::vector<std::string> parts;
    for (const auto& t : tok) {
        parts.push_back(t);
    }
    assert(parts.size() == 3);
    assert(parts[0] == "foo" && parts[1] == "bar" && parts[2] == "baz");
    std::string s2 = "a b  c";
    boost::tokenizer<> tok2(s2);
    parts.clear();
    for (const auto& t : tok2) {
        parts.push_back(t);
    }
    assert(parts.size() == 3 && parts[2] == "c");
    std::string s3 = "1,2,3";
    boost::tokenizer<boost::escaped_list_separator<char>> tok3(s3);
    parts.clear();
    for (const auto& t : tok3) {
        parts.push_back(t);
    }
    assert(parts.size() == 3 && parts[1] == "2");
    auto it = boost::make_token_iterator<std::string>(s.begin(), s.end(), boost::char_separator<char>(","));
    assert(*it == "foo");
    return 0;
}
