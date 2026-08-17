// boost.stl_interfaces smoke — view_interface CRTP
#include "test_assert.hpp"
import std;
import boost.stl_interfaces;

template <class T>
struct MyView : boost::stl_interfaces::view_interface<MyView<T>> {
    MyView(T* p, T* q) : p_(p), q_(q) {}
    T* begin() const { return p_; }
    T* end() const { return q_; }
    T* p_;
    T* q_;
};

int main() {
    int arr[] = {1, 2, 3, 4};
    MyView<int> v(arr, arr + 4);
    assert(v.size() == 4);
    assert(!v.empty());
    assert(v.front() == 1 && v.back() == 4);
    assert(v[2] == 3);
    assert(v.begin()[1] == 2);
    int count = 0;
    for (int x : v) {
        count += x;
    }
    assert(count == 10);
    return 0;
}
