// boost.property_tree smoke — tree data structure with paths
#include "test_assert.hpp"
import std;
import boost.property_tree;

int main() {
    boost::property_tree::ptree pt;
    pt.put("name", "boost");
    pt.put("version.major", 1);
    pt.put("version.minor", 91);
    assert(pt.get<std::string>("name") == "boost");
    assert(pt.get<int>("version.major") == 1);
    assert(pt.get<int>("version.minor") == 91);
    assert(pt.get<int>("missing", 42) == 42);
    boost::property_tree::ptree child = pt.get_child("version");
    assert(child.get<int>("major") == 1);
    assert(pt.count("name") == 1);
    pt.put("version.minor", 90);
    assert(pt.get<int>("version.minor") == 90);
    pt.erase("version");
    assert(pt.get<int>("version.major", -1) == -1);
    return 0;
}
