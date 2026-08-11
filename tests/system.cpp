// boost.system smoke — error_code/error_condition/errc/result
#include "test_assert.hpp"
import std;
import boost.system;

int main() {
    boost::system::error_code ec = boost::system::errc::make_error_code(
        boost::system::errc::no_such_file_or_directory);
    assert(ec);
    assert(ec.category() == boost::system::generic_category());
    assert(ec.value() != 0);
    boost::system::error_code ok;
    assert(!ok);
    boost::system::error_condition cond = boost::system::errc::make_error_condition(
        boost::system::errc::timed_out);
    assert(cond == boost::system::errc::timed_out);
    assert(ec != boost::system::errc::success);
    boost::system::result<int> r(42);
    assert(r);
    assert(r.value() == 42);
    boost::system::result<int> e = boost::system::errc::make_error_code(
        boost::system::errc::operation_not_permitted);
    assert(!e);
    assert(e.error());
    assert(e.error().value() != 0);
    boost::system::error_code ec2 = boost::system::errc::make_error_code(
        boost::system::errc::no_such_file_or_directory);
    assert(ec == ec2);
    assert(boost::system::system_category().name() != nullptr);
    return 0;
}
