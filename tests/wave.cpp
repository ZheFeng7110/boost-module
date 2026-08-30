// boost.wave smoke — compiled lib linkage (instantiate_re2c_lexer /
// instantiate_cpp_grammar / token_ids TUs)
#include "test_assert.hpp"
import std;
import boost.wave;

int main() {
    typedef boost::wave::cpplexer::lex_token<> token_type;
    typedef boost::wave::cpplexer::lex_iterator<token_type> lex_iterator_type;
    typedef boost::wave::context<std::string::const_iterator,
                                 lex_iterator_type> context_type;

    std::string input = "#define X 42\nint x = X;\n";
    context_type ctx(input.begin(), input.end(), "wave_smoke.cpp");
    ctx.set_language(boost::wave::language_support(
        boost::wave::support_cpp | boost::wave::support_option_long_long));

    std::ostringstream out;
    int value_tokens = 0;
    for (auto it = ctx.begin(); it != ctx.end(); ++it) {
        std::string val((*it).get_value().c_str());
        out << val;
        if (val == "42")
            ++value_tokens;
    }
    assert(value_tokens == 1);          // X expanded exactly once
    assert(out.str().find("int x = 42;") != std::string::npos);
    return 0;
}
