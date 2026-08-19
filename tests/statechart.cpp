// boost.statechart smoke — simple state machine (mpl::list is include-only;
// mixing include + import is standard-compliant, but gcc 16 ODR-conflicts on
// it — same redefinition pattern as describe.cpp — so the import is skipped on
// gcc, keeping the test pure-header)
#include "test_assert.hpp"
#include <cassert>
#if !defined(__GNUC__) || defined(__clang__)
import boost.statechart;
#endif
#include <boost/mpl/list.hpp>
#if defined(__GNUC__) && !defined(__clang__)
// gcc: import skipped above — bring the statechart API in via header instead.
#include <boost/statechart.hpp>
#endif

namespace sc = boost::statechart;
namespace mpl = boost::mpl;

struct EvStart : sc::event<EvStart> {};
struct EvStop : sc::event<EvStop> {};

struct Machine : sc::state_machine<Machine, struct Idle> {};
struct Idle : sc::simple_state<Idle, Machine> {
    typedef sc::transition<EvStart, struct Running> reactions;
};
struct Running : sc::simple_state<Running, Machine> {
    typedef sc::transition<EvStop, Idle> reactions;
};

int main() {
    Machine m;
    m.initiate();
    assert(m.state_cast<const Idle*>() != nullptr);
    m.process_event(EvStart());
    assert(m.state_cast<const Running*>() != nullptr);
    m.process_event(EvStop());
    assert(m.state_cast<const Idle*>() != nullptr);
    m.terminate();
    return 0;
}
