// boost.openmethod smoke — open methods (macros are include-only; mixing
// include + import is standard-compliant)
#include "test_assert.hpp"
#include <cassert>
#include <string>
import boost.openmethod;
#include <boost/openmethod.hpp>

struct A {
    virtual ~A() = default;
};
struct B : A {};

BOOST_OPENMETHOD_CLASSES(A, B);

BOOST_OPENMETHOD(kind, (boost::openmethod::virtual_ptr<A>), int);

BOOST_OPENMETHOD_OVERRIDE(kind, (boost::openmethod::virtual_ptr<A>), int) {
    return 1;
}

BOOST_OPENMETHOD_OVERRIDE(kind, (boost::openmethod::virtual_ptr<B>), int) {
    return 2;
}

int main() {
    boost::openmethod::initialize();
    A a;
    B b;
    assert(kind(a) == 1);
    assert(kind(b) == 2);
    boost::openmethod::finalize();
    return 0;
}
