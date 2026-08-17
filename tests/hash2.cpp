// boost.hash2 smoke — hashing algorithms
#include "test_assert.hpp"
import std;
import boost.hash2;

int main() {
    boost::hash2::fnv1a_32 h;
    boost::hash2::default_flavor flavor;
    boost::hash2::hash_append(h, flavor, 'a');
    boost::hash2::hash_append(h, flavor, 'b');
    auto r1 = boost::hash2::get_integral_result<std::uint32_t>(h);
    assert(r1 != 0);
    boost::hash2::fnv1a_32 h2;
    boost::hash2::hash_append(h2, flavor, 'a');
    boost::hash2::hash_append(h2, flavor, 'b');
    assert(r1 == boost::hash2::get_integral_result<std::uint32_t>(h2));
    boost::hash2::fnv1a_32 h3;
    boost::hash2::hash_append(h3, flavor, 'a');
    assert(r1 != boost::hash2::get_integral_result<std::uint32_t>(h3));
    boost::hash2::fnv1a_32 h4;
    boost::hash2::hash_append(h4, flavor, std::string("hello"));
    auto r4 = boost::hash2::get_integral_result<std::uint32_t>(h4);
    boost::hash2::fnv1a_32 h5;
    boost::hash2::hash_append(h5, flavor, std::string("hello"));
    assert(r4 == boost::hash2::get_integral_result<std::uint32_t>(h5));
    return 0;
}
