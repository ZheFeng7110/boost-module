// boost.poly_collection smoke — polymorphic container
#include "test_assert.hpp"
import std;
import boost.poly_collection;

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
