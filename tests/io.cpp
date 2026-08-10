// boost.io smoke — quoted, ostream_joiner, saver types
import std;
import boost.io;

int main() {
    std::ostringstream os;
    os << boost::io::quoted(std::string("a \"b\" c"));
    if (os.str() != "\"a \\\"b\\\" c\"") return 1;
    std::istringstream is("\"quoted value\" rest");
    std::string s;
    is >> boost::io::quoted(s);
    if (s != "quoted value") return 2;
    {
        boost::io::ios_flags_saver saver(os);
        os.setf(std::ios::hex, std::ios::basefield);
        os << 15;
    }
    if (os.str().back() != 'f') return 3;
    os.str("");
    os.clear();
    std::vector<int> v{1, 2, 3};
    auto joiner = boost::io::make_ostream_joiner(os, ",");
    std::copy(v.begin(), v.end(), joiner);
    if (os.str() != "1,2,3") return 4;
    os.str("");
    boost::io::ostream_put(os, "xy", 2);
    if (os.str() != "xy") return 5;
    return 0;
}
