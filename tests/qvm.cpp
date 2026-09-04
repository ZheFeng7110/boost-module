// boost.qvm smoke — vector/quaternion operations (header-only math)
#include "test_assert.hpp"
import std;
import boost.qvm;

int main() {
    namespace qvm = boost::qvm;

    qvm::vec<float, 3> v1{1.0f, 0.0f, 0.0f};
    qvm::vec<float, 3> v2{0.0f, 1.0f, 0.0f};
    float dot = qvm::dot(v1, v2);
    assert(dot == 0.0f);

    qvm::vec<float, 3> sum = v1 + v2;
    assert(sum.a[0] == 1.0f && sum.a[1] == 1.0f && sum.a[2] == 0.0f);

    qvm::vec<float, 3> c = qvm::cross(v1, v2);
    assert(c.a[2] == 1.0f);

    qvm::quat<float> q1{1.0f, 0.0f, 0.0f, 0.0f};  // identity
    assert(qvm::mag(q1) == 1.0f);

    qvm::mat<float, 3, 3> m = qvm::rotz_mat<3>(1.5707963f);
    qvm::vec<float, 3> rotated = m * v1;
    assert(rotated.a[1] > 0.99f);
    return 0;
}
