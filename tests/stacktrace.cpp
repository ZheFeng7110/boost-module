// boost.stacktrace smoke — compiled lib linkage (basic impl, BOOST_STACKTRACE_LINK)
import std;
import boost.stacktrace;

[[gnu::noinline]] void fill(boost::stacktrace::stacktrace& st) { st = boost::stacktrace::stacktrace(); }

int main() {
    boost::stacktrace::stacktrace st = boost::stacktrace::stacktrace();
    if (st.size() == 0) return 1;
    boost::stacktrace::frame f = st[0];
    if (f.address() == nullptr) return 2;
    std::string s = boost::stacktrace::to_string(st);
    if (s.empty()) return 3;
    std::string f2 = boost::stacktrace::to_string(f);
    if (f2.empty()) return 4;
    boost::stacktrace::stacktrace st2;
    fill(st2);
    if (st2.size() == 0) return 5;
    return 0;
}
