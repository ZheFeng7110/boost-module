// boost.chrono smoke — compiled lib linkage (clocks/duration arithmetic)
import std;
import boost.chrono;

int main() {
    boost::chrono::steady_clock::time_point t0 = boost::chrono::steady_clock::now();
    boost::chrono::steady_clock::time_point t1 = boost::chrono::steady_clock::now();
    boost::chrono::nanoseconds ns = t1 - t0;
    if (ns.count() < 0) return 1;

    boost::chrono::system_clock::time_point tp = boost::chrono::system_clock::now();
    boost::chrono::system_clock::time_point epoch = boost::chrono::system_clock::from_time_t(0);
    boost::chrono::seconds since = boost::chrono::duration_cast<boost::chrono::seconds>(tp - epoch);
    if (since.count() <= 0) return 2;

    boost::chrono::seconds a(90);
    boost::chrono::minutes b = boost::chrono::duration_cast<boost::chrono::minutes>(a);
    if (b.count() != 1) return 3;
    if (boost::chrono::floor<boost::chrono::minutes>(a) != b) return 4;
    if (boost::chrono::ceil<boost::chrono::minutes>(a).count() != 2) return 5;
    if (boost::chrono::round<boost::chrono::minutes>(a).count() != 2) return 6;

    boost::chrono::duration<double> d(1.5);
    boost::chrono::milliseconds ms = boost::chrono::duration_cast<boost::chrono::milliseconds>(d);
    if (ms.count() != 1500) return 7;

    boost::chrono::steady_clock::time_point later = t0 + boost::chrono::seconds(1);
    if (!(later > t0)) return 8;
    if (later - t0 != boost::chrono::seconds(1)) return 9;

    auto now = boost::chrono::steady_clock::now();
    if (now.time_since_epoch().count() == 0) return 10;
    return 0;
}
