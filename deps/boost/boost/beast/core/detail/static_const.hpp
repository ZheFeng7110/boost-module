//
// Copyright (c) 2016-2019 Vinnie Falco (vinnie dot falco at gmail dot com)
//
// Distributed under the Boost Software License, Version 1.0. (See accompanying
// file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
//
// Official repository: https://github.com/boostorg/beast
//

#ifndef BOOST_BEAST_DETAIL_STATIC_CONST_HPP
#define BOOST_BEAST_DETAIL_STATIC_CONST_HPP

/*  This is a derivative work, original copyright:

    Copyright Eric Niebler 2013-present

    Use, modification and distribution is subject to the
    Boost Software License, Version 1.0. (See accompanying
    file LICENSE_1_0.txt or copy at
    http://www.boost.org/LICENSE_1_0.txt)

    Project home: https://github.com/ericniebler/range-v3
*/

namespace boost {
namespace beast {
namespace detail {

template<typename T>
struct static_const
{
    static constexpr T value {};
};

template<typename T>
constexpr T static_const<T>::value;

// boost-module M12 vendor patch: anonymous namespace -> inline constexpr.
// The TU-local variable is referenced from the module face; when a beast CMI
// and a consumer GMF (mqtt5 etc.) both carry the _GLOBAL__N_1 copy, gcc emits
// the same-mangled symbol twice (M11 §7.4 print_helper family). An inline
// constexpr variable keeps the spelling and merges the definitions.
#define BOOST_BEAST_INLINE_VARIABLE(name, type) \
    inline constexpr auto& name = \
        ::boost::beast::detail::static_const<type>::value;

} // detail
} // beast
} // boost

#endif
