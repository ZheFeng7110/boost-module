// boost.functional smoke — old-style binders / negators / mem_fun / factory
#include "test_assert.hpp"
import std;
import boost.functional;

int main() {
    struct less_t {
        typedef int first_argument_type;
        typedef int second_argument_type;
        typedef bool result_type;
        bool operator()(int a, int b) const { return a < b; }
    };
    struct minus_t {
        typedef int first_argument_type;
        typedef int second_argument_type;
        typedef int result_type;
        int operator()(int a, int b) const { return a - b; }
    };
    less_t less_;
    minus_t minus_;
    assert(boost::bind1st(less_, 5)(6));
    assert(!boost::bind2nd(less_, 5)(6));
    assert(boost::not1(boost::bind2nd(less_, 5))(6));
    assert(boost::bind1st(minus_, 10)(4) == 6);
    struct Foo {
        int get() const { return 42; }
    };
    Foo f;
    assert(boost::mem_fn(&Foo::get)(f) == 42);
    assert(boost::mem_fun(&Foo::get)(&f) == 42);
    auto p = boost::factory<std::vector<int>*>()();
    assert(p->empty());
    delete p;
    auto sp = boost::factory<std::shared_ptr<int>>()(7);
    assert(*sp == 7);
    return 0;
}
