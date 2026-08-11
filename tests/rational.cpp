// boost.rational smoke — arithmetic, comparisons, stream I/O
#include "test_assert.hpp"
import std;
import boost.rational;

int main() {
    boost::rational<int> a(1, 2);
    boost::rational<int> b(1, 3);
    assert(a.numerator() == 1 && a.denominator() == 2);
    boost::rational<int> sum = a + b;
    assert(sum == boost::rational<int>(5, 6));
    boost::rational<int> prod = a * b;
    assert(prod == boost::rational<int>(1, 6));
    assert(a > b && b < a);
    boost::rational<int> c = a;
    assert(a == c);
    assert(a - b == boost::rational<int>(1, 6));
    boost::rational<int> d = -a;
    assert(d + a == 0);
    boost::rational<int> reduced(4, 8);
    assert(reduced.numerator() == 1 && reduced.denominator() == 2);
    boost::rational<int> from_int(3);
    assert(from_int == 3);
    std::ostringstream os;
    os << a;
    assert(os.str() == "1/2");
    assert(boost::rational<int>(0) == 0);
    return 0;
}
