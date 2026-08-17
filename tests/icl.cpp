// boost.icl smoke — interval set/map
#include "test_assert.hpp"
import std;
import boost.icl;

int main() {
    boost::icl::interval_set<int> s;
    s.add(1);
    s.add(boost::icl::interval<int>::closed(3, 5));
    assert(s.find(1) != s.end());
    assert(s.find(3) != s.end());
    assert(s.find(5) != s.end());
    assert(s.find(2) == s.end());
    assert(s.find(6) == s.end());
    assert(s.iterative_size() == 2);
    boost::icl::interval_map<int, int> m;
    m += std::make_pair(boost::icl::interval<int>::open(0, 10), 1);
    m += std::make_pair(boost::icl::interval<int>::open(5, 15), 2);
    assert(m.find(2)->second == 1);
    assert(m.find(7)->second == 3);
    assert(m.find(12)->second == 2);
    return 0;
}
