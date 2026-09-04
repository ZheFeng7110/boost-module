// boost.numeric smoke — conversion cast + ublas vector ops + odeint stepper
// NB: boost::numeric::interval<double> is NOT instantiable from the module
// face — its default policies<> argument involves the rounded_math<double>
// explicit specialization, which a module CMI cannot carry (M9 §6 family).
// Consumers include <boost/numeric/interval/interval.hpp> for intervals.
#include "test_assert.hpp"
import std;
import boost.numeric;

int main() {
    namespace bn = boost::numeric;
    namespace ub = boost::numeric::ublas;

    // numeric conversion cast: narrowing with range checking
    double d = 3.7;
    int i = boost::numeric_cast<int>(d);
    assert(i == 3);

    // ublas vector operations
    ub::vector<double> v(3, 1.0);
    ub::vector<double> w(3, 2.0);
    ub::vector<double> sum = v + w;
    assert(sum(0) == 3.0 && sum(1) == 3.0 && sum(2) == 3.0);
    assert(inner_prod(v, w) == 6.0);

    // odeint: constant-size stepper on a plain array state
    using state_t = std::array<double, 1>;
    state_t x{1.0};
    bn::odeint::runge_kutta4<state_t> stepper;
    stepper.do_step([](const state_t& s, state_t& dxdt, double) { dxdt[0] = -s[0]; },
                    x, 0.0, 0.1);
    assert(x[0] > 0.88 && x[0] < 0.91);
    return 0;
}
