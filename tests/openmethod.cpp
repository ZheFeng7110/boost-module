// boost.openmethod smoke — pure include (C1 downgrade, 2026-09-06: the module
// is gone; the public API is the BOOST_OPENMETHOD* macro family — M10 rule —
// and gcc 16 ODR-conflicts on include+import mixing, see describe.cpp / the
// C1 plan §1.1). initialize()/finalize() live in a separate header the old
// module GMF included; include it explicitly here.
#include "test_assert.hpp"
#include <cassert>
#include <string>
#include <boost/openmethod.hpp>
#include <boost/openmethod/initialize.hpp>

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
