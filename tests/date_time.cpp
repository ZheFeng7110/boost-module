// boost.date_time smoke — compiled lib linkage (greg_month TU: month name
// / special_values symbols)
#include "test_assert.hpp"
import std;
import boost.date_time;

int main() {
    boost::gregorian::date d(2026, 8, 30);
    assert(d.year() == 2026 && d.month() == 8 && d.day() == 30);
    assert(d.day_of_week().as_number() == 0); // 2026-08-30 is a Sunday

    boost::gregorian::date d2 = d + boost::gregorian::days(1);
    assert(d2.day() == 31);

    boost::gregorian::date e(2026, 2, 28);
    assert((e + boost::gregorian::days(1)).month() == 3); // non-leap year

    // month name tables live in the greg_month TU
    assert(d.month().as_short_string() != nullptr);

    // posix_time built over gregorian
    boost::posix_time::ptime t(d, boost::posix_time::hours(12));
    assert(t.date().year() == 2026);
    assert(t.time_of_day() == boost::posix_time::hours(12));
    return 0;
}
