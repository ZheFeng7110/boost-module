// boost.contract smoke — compiled lib linkage (contract.cpp: violation handler)
#include "test_assert.hpp"
import std;
import boost.contract;

int main() {
    int pre_runs = 0;
    {
        boost::contract::check c = boost::contract::function()
            .precondition([&] { ++pre_runs; });
        // preconditions run when the contract object is constructed
        assert(pre_runs == 1);
    }
    assert(pre_runs == 1);
    return 0;
}
