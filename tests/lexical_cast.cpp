// boost.lexical_cast smoke — string conversion
#include "test_assert.hpp"
import std;
import boost.lexical_cast;

int main() {
    assert(boost::lexical_cast<int>("42") == 42);
    assert(boost::lexical_cast<std::string>(42) == "42");
    assert(boost::lexical_cast<double>("2.5") == 2.5);
    bool caught = false;
    try {
        (void)boost::lexical_cast<int>("not-a-number");
    } catch (boost::bad_lexical_cast const&) {
        caught = true;
    }
    assert(caught);
    return 0;
}
