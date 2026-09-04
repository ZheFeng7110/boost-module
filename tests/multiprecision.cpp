// boost.multiprecision smoke — cpp_int arbitrary precision arithmetic
// (the free str() overload is not part of the module face; use the .str()
// member of number<>, which is exported with its class)
#include "test_assert.hpp"
import std;
import boost.multiprecision;

int main() {
    namespace mp = boost::multiprecision;

    mp::cpp_int big("123456789012345678901234567890");
    mp::cpp_int doubled = big * 2;
    assert(doubled.str() == "246913578024691357802469135780");
    assert(doubled / big == 2);

    mp::cpp_int fact = 1;
    for (int i = 2; i <= 20; ++i) {
        fact *= i;
    }
    assert(fact.str() == "2432902008176640000");

    mp::cpp_int a = 12345;
    mp::cpp_int b = 6789;
    assert(mp::gcd(a, b) == 3);
    assert(mp::lcm(a, b) == a * b / mp::gcd(a, b));

    mp::cpp_rational r(3, 8);
    mp::cpp_rational s(1, 8);
    assert((r + s) == mp::cpp_rational(1, 2));
    return 0;
}
