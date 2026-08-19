// boost.poly_collection smoke — polymorphic container
//
// gcc 16.1.0: module consumers of boost.poly_collection fail to instantiate
// the type_info_map's std::unordered_map<const std::type_info*, ...> — the
// std::hash<_Tp*> partial specialization is not found in the module
// instantiation context, so the primary (non-copyable) template is used
// ("hash function must be copy constructible", linux-gcc CI). The module
// import is skipped on gcc and the test stays pure header.
#include "test_assert.hpp"
#include <cassert>
#if !defined(__GNUC__) || defined(__clang__)
import std;
import boost.poly_collection;
#else
#include <iterator>
#include <boost/poly_collection/base_collection.hpp>
#endif

struct Shape {
    virtual ~Shape() = default;
    virtual int kind() const { return 0; }
};
struct Circle : Shape {
    int kind() const override { return 1; }
};
struct Square : Shape {
    int kind() const override { return 2; }
};

int main() {
    boost::poly_collection::base_collection<Shape> c;
    c.insert(Circle{});
    c.insert(Square{});
    c.insert(Square{});
    assert(c.size() == 3);
    assert(std::distance(c.segment<Circle>().begin(),
                         c.segment<Circle>().end()) == 1);
    assert(std::distance(c.segment<Square>().begin(),
                         c.segment<Square>().end()) == 2);
    int kinds = 0;
    for (const Shape& s : c) {
        kinds += s.kind();
    }
    assert(kinds == 5);
    c.erase(c.begin(), c.end());
    assert(c.empty());
    return 0;
}
