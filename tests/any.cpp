// boost.any smoke — any, any_cast (value/ref/pointer), empty
import std;
import boost.any;

int main() {
    boost::any a(5);
    if (boost::any_cast<int>(a) != 5) return 1;
    boost::any b(std::string("abc"));
    if (boost::any_cast<std::string>(b) != "abc") return 2;
    boost::any_cast<std::string&>(b) = "xyz";
    if (boost::any_cast<std::string>(b) != "xyz") return 3;
    if (boost::any_cast<int>(&b) != nullptr) return 4;
    if (*boost::any_cast<std::string>(&b) != "xyz") return 5;
    try {
        (void)boost::any_cast<int>(b);
        return 6;
    } catch (boost::bad_any_cast const&) {
    }
    boost::any empty;
    if (!empty.empty()) return 7;
    boost::any c = b;
    if (boost::any_cast<std::string>(c) != "xyz") return 8;
    return 0;
}
