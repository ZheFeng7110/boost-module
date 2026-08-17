// boost.smart_ptr smoke — shared_ptr / weak_ptr / make_shared / scoped_ptr
#include "test_assert.hpp"
import std;
import boost.smart_ptr;

int main() {
    boost::shared_ptr<int> a = boost::make_shared<int>(42);
    assert(*a == 42);
    assert(a.use_count() == 1);
    boost::shared_ptr<int> b = a;
    assert(a.use_count() == 2 && b.use_count() == 2);
    b.reset();
    assert(a.unique());
    boost::weak_ptr<int> w = a;
    assert(w.use_count() == 1);
    boost::shared_ptr<int> c = w.lock();
    assert(c && *c == 42);
    assert(boost::static_pointer_cast<int>(a) == a);
    boost::shared_ptr<int> d = boost::make_shared<int>(7);
    assert(boost::shared_ptr<int>(d) == d);
    boost::scoped_ptr<int> sc(new int(5));
    assert(*sc == 5);
    return 0;
}
