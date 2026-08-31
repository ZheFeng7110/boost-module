/*
Copyright 2019-2020 Glen Joseph Fernandes
(glenjofe@gmail.com)

Distributed under the Boost Software License, Version 1.0.
(http://www.boost.org/LICENSE_1_0.txt)
*/
#ifndef BOOST_IO_DETAIL_BUFFER_FILL_HPP
#define BOOST_IO_DETAIL_BUFFER_FILL_HPP

#include <iosfwd>
#include <cstddef>

namespace boost {
namespace io {
namespace detail {

template<class charT, class traits>
inline bool
buffer_fill(std::basic_streambuf<charT, traits>& buf, charT ch,
    std::size_t size)
{
    charT fill[] = { ch, ch, ch, ch, ch, ch, ch, ch };
    // M11 vendored edit (gcc C++23 modules): the unnamed enum inside this
    // inline template failed to stream consistently across CMIs that include
    // this header from different module faces (boost.utility via
    // utility/string_view.hpp, boost.filesystem/wave via filesystem/path.hpp →
    // io/quoted.hpp) — gcc hard-errors "definition of enum ... does not match"
    // when a consumer TU loads both pendings. A constexpr local is
    // behavior-identical and streams fine. Replay after re-running
    // import_boost (see M11 doc §6.9).
    constexpr std::size_t chunk = sizeof fill / sizeof(charT);
    for (; size > chunk; size -= chunk) {
        if (static_cast<std::size_t>(buf.sputn(fill, chunk)) != chunk) {
            return false;
        }
    }
    return static_cast<std::size_t>(buf.sputn(fill, size)) == size;
}

} /* detail */
} /* io */
} /* boost */

#endif
