// boost.msm — include-only smoke (M10 T3: the state-machine tables are built
// by the BOOST_MSM_* macro face + mpl rows, no module; the import proves
// import+include mixing in one TU)
#include "test_assert.hpp"
#include <boost/mpl/vector.hpp>
import boost.config;
#include <boost/msm/back/state_machine.hpp>
#include <boost/msm/front/state_machine_def.hpp>
#include <boost/msm/front/functor_row.hpp>

namespace msm = boost::msm;

struct EvStart {};
struct EvStop {};

int running_entries = 0;

struct Fsm_ : public msm::front::state_machine_def<Fsm_> {
    struct Idle : msm::front::state<> {};
    struct Running : msm::front::state<> {
        template <class Event, class Fsm>
        void on_entry(Event const&, Fsm&) {
            ++running_entries;
        }
    };
    typedef Idle initial_state;
    struct transition_table
        : boost::mpl::vector<
              msm::front::Row<Idle, EvStart, Running, msm::front::none,
                              msm::front::none>,
              msm::front::Row<Running, EvStop, Idle, msm::front::none,
                              msm::front::none>> {};
};

typedef msm::back::state_machine<Fsm_> Fsm;

int main() {
    Fsm f;
    f.start();
    assert(running_entries == 0);
    f.process_event(EvStart());
    assert(running_entries == 1);
    f.process_event(EvStop());
    f.process_event(EvStart());
    assert(running_entries == 2);
    return 0;
}
