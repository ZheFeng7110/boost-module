// boost.system smoke — error_code/error_condition/errc/result
import std;
import boost.system;

int main() {
    boost::system::error_code ec = boost::system::errc::make_error_code(
        boost::system::errc::no_such_file_or_directory);
    if (!ec) return 1;
    if (ec.category() != boost::system::generic_category()) return 2;
    if (ec.value() == 0) return 3;
    boost::system::error_code ok;
    if (ok) return 4;
    boost::system::error_condition cond = boost::system::errc::make_error_condition(
        boost::system::errc::timed_out);
    if (cond != boost::system::errc::timed_out) return 5;
    if (ec == boost::system::errc::success) return 6;
    boost::system::result<int> r(42);
    if (!r) return 7;
    if (r.value() != 42) return 8;
    boost::system::result<int> e = boost::system::errc::make_error_code(
        boost::system::errc::operation_not_permitted);
    if (e) return 9;
    if (!e.error()) return 10;
    if (e.error().value() == 0) return 11;
    boost::system::error_code ec2 = boost::system::errc::make_error_code(
        boost::system::errc::no_such_file_or_directory);
    if (ec != ec2) return 12;
    if (boost::system::system_category().name() == nullptr) return 13;
    return 0;
}
