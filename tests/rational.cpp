// boost.rational smoke — arithmetic, comparisons, stream I/O
import std;
import boost.rational;

int main() {
    boost::rational<int> a(1, 2);
    boost::rational<int> b(1, 3);
    if (a.numerator() != 1 || a.denominator() != 2) return 1;
    boost::rational<int> sum = a + b;
    if (sum != boost::rational<int>(5, 6)) return 2;
    boost::rational<int> prod = a * b;
    if (prod != boost::rational<int>(1, 6)) return 3;
    if (!(a > b) || !(b < a)) return 4;
    boost::rational<int> c = a;
    if (a != c) return 5;
    if (a - b != boost::rational<int>(1, 6)) return 6;
    boost::rational<int> d = -a;
    if (d + a != 0) return 7;
    boost::rational<int> reduced(4, 8);
    if (reduced.numerator() != 1 || reduced.denominator() != 2) return 8;
    boost::rational<int> from_int(3);
    if (from_int != 3) return 9;
    std::ostringstream os;
    os << a;
    if (os.str() != "1/2") return 10;
    if (boost::rational<int>(0) != 0) return 11;
    return 0;
}
