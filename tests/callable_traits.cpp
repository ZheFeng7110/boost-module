// boost.callable_traits smoke — signature traits
#include "test_assert.hpp"
import std;
import boost.callable_traits;

int main() {
    using fn = int (*)(double, char);
    static_assert(std::is_same<boost::callable_traits::return_type_t<fn>, int>::value);
    static_assert(std::is_same<boost::callable_traits::args_t<fn>,
                  std::tuple<double, char>>::value);
    static_assert(std::is_same<boost::callable_traits::function_type_t<fn>,
                  int (double, char)>::value);
    using fnt = int(double, char);
    static_assert(std::is_same<boost::callable_traits::add_member_const_t<fnt>,
                  int (double, char) const>::value);
    using mf = int (std::string::*)() const;
    static_assert(boost::callable_traits::is_const_member<mf>::value);
    static_assert(std::is_same<boost::callable_traits::class_of_t<mf>,
                  std::string>::value);
    return 0;
}
