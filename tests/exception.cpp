// boost.exception smoke — include-only (M11 downgrade: the clone_impl pendings
// in a boost.exception CMI trip gcc 16.1 "recursive lazy load" in every real
// consumer TU, so the library follows the T3 consumer rule; throw_exception
// stays a module). throw_exception wraps the error with
// enable_current_exception so the exception_ptr clone carries the error_info
// map; the error_info tag type is declared once at namespace scope so both
// sites name the same type.
#include "test_assert.hpp"
// include-only (T3 consumer rule, same as the library face): importing a
// module next to <boost/exception/all.hpp> trips the gcc 16.1 CMI merge bug
// (std::__byte_operand / <cstddef> conflicting declarations), so the smoke
// test consumes the headers directly.
#include <boost/exception/all.hpp>
#include <boost/throw_exception.hpp>

struct tag_int {};

struct my_error : std::exception, boost::exception {};

int main() {
    boost::exception_ptr saved;
    try {
        my_error e;
        e << boost::error_info<tag_int, int>(42);
        boost::throw_exception(e);
    } catch (...) {
        saved = boost::current_exception();
    }
    assert(saved != boost::exception_ptr());

    bool caught = false;
    try {
        boost::rethrow_exception(saved);
    } catch (my_error& e) {
        caught = true;
        int const* v = boost::get_error_info<boost::error_info<tag_int, int>>(e);
        assert(v != nullptr && *v == 42);
        std::string di = boost::diagnostic_information(e);
        assert(!di.empty());
    }
    assert(caught);
    return 0;
}
