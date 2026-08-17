// boost.logic smoke — tribool
// NB: assert(tribool_expr) is broken on MSVC's assert macro — the macro
// `(!!(x)) || (_wassert(...), 0)` always evaluates the right side when the
// expression has a user-defined operator|| (no short-circuit), so _wassert
// aborts regardless of the value. Always convert to bool first.
#include "test_assert.hpp"
import std;
import boost.logic;

int main() {
    boost::logic::tribool t = boost::logic::indeterminate;
    assert(boost::logic::indeterminate(t));
    boost::logic::tribool t2(boost::logic::indeterminate);
    assert(boost::logic::indeterminate(t == t2));
    boost::logic::tribool tr = true;
    boost::logic::tribool fa = false;
    assert(bool(tr && !fa));
    assert(bool((tr || fa) == true));
    assert(bool((tr && fa) == false));
    assert(bool((!tr) == false));
    boost::logic::tribool ind = boost::logic::indeterminate;
    assert(boost::logic::indeterminate(!ind));
    assert(bool((ind || true) == true));
    assert(boost::logic::indeterminate(ind && true));
    return 0;
}
