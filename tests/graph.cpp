// boost.graph smoke — compiled lib linkage (graphml TU: read_graphml).
// read_graphviz is known to fail-fast under the module consumer on this
// toolchain (M11 doc §6), so the TU-linkage proof uses read_graphml.
#include "test_assert.hpp"
import std;
import boost.graph;
import boost.property_map;

int main() {
    boost::adjacency_list<> g;
    std::istringstream in(
        "<?xml version='1.0'?>\n"
        "<graphml xmlns='http://graphml.graphdrawing.org/xmlns'>\n"
        "  <graph id='G' edgedefault='directed'>\n"
        "    <node id='a'/><node id='b'/>\n"
        "    <edge source='a' target='b'/>\n"
        "  </graph>\n"
        "</graphml>");
    boost::dynamic_properties dp;
    boost::read_graphml(in, g, dp);
    assert(boost::num_vertices(g) == 2);
    assert(boost::num_edges(g) == 1);

    // header-only surface over the parsed graph
    boost::adjacency_list<>::vertex_descriptor v = boost::vertex(0, g);
    assert(boost::out_degree(v, g) == 1);
    return 0;
}
