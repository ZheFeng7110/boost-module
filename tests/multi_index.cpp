// boost.multi_index smoke — ordered_unique index container
#include "test_assert.hpp"
import std;
import boost.multi_index;

struct Rec {
    int id;
    std::string name;
};

int main() {
    using Table = boost::multi_index::multi_index_container<
        Rec,
        boost::multi_index::indexed_by<
            boost::multi_index::ordered_unique<
                boost::multi_index::member<Rec, int, &Rec::id>>>>;
    Table t;
    t.insert(Rec{1, "a"});
    t.insert(Rec{2, "b"});
    assert(t.size() == 2);
    auto& idx = t.template get<0>();
    auto it = idx.find(2);
    assert(it != idx.end() && it->name == "b");
    assert(idx.count(1) == 1);
    assert(!t.insert(Rec{1, "dup"}).second);
    assert(t.size() == 2);
    idx.erase(1);
    assert(t.size() == 1);
    return 0;
}
