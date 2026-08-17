// boost.throw_exception smoke — throw_exception / wrapexcept
#include "test_assert.hpp"
import std;
import boost.throw_exception;

int main() {
    bool caught = false;
    try {
        boost::throw_exception(std::runtime_error("boom"));
    } catch (std::runtime_error const& e) {
        caught = std::string(e.what()) == "boom";
    }
    assert(caught);
    caught = false;
    try {
        boost::throw_exception(std::out_of_range("range"));
    } catch (std::out_of_range const&) {
        caught = true;
    }
    assert(caught);
    boost::wrapexcept<std::runtime_error> w(std::runtime_error("wrapped"));
    assert(std::string(w.what()) == "wrapped");
    caught = false;
    try {
        boost::throw_with_location(std::logic_error("x"), boost::source_location{});
    } catch (std::logic_error const&) {
        caught = true;
    }
    assert(caught);
    return 0;
}
