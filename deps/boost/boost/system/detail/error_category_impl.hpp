#ifndef BOOST_SYSTEM_DETAIL_ERROR_CATEGORY_IMPL_HPP_INCLUDED
#define BOOST_SYSTEM_DETAIL_ERROR_CATEGORY_IMPL_HPP_INCLUDED

//  Copyright Beman Dawes 2006, 2007
//  Copyright Christoper Kohlhoff 2007
//  Copyright Peter Dimov 2017, 2018
//
//  Distributed under the Boost Software License, Version 1.0. (See accompanying
//  file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
//
//  See library home page at http://www.boost.org/libs/system

#include <boost/system/detail/error_category.hpp>
#include <boost/system/detail/error_condition.hpp>
#include <boost/system/detail/error_code.hpp>
#include <boost/system/detail/snprintf.hpp>
#include <boost/system/detail/config.hpp>
#include <boost/config.hpp>
#include <string>
#include <cstring>

namespace boost
{
namespace system
{

// error_category default implementation

BOOST_SYSTEM_CXX20_CONSTEXPR inline error_condition error_category::default_error_condition( int ev ) const noexcept
{
    return error_condition( ev, *this );
}

BOOST_SYSTEM_CXX20_CONSTEXPR inline bool error_category::equivalent( int code, error_condition const& condition ) const noexcept
{
    return default_error_condition( code ) == condition;
}

BOOST_SYSTEM_CXX20_CONSTEXPR inline bool error_category::equivalent( error_code const& code, int condition ) const noexcept
{
    return code.equals( condition, *this );
}

inline char const* error_category::message( int ev, char* buffer, std::size_t len ) const noexcept
{
    if( len == 0 )
    {
        return buffer;
    }

    if( len == 1 )
    {
        buffer[0] = 0;
        return buffer;
    }

#if !defined(BOOST_NO_EXCEPTIONS)
    try
#endif
    {
        detail::snprintf( buffer, len, "%s", this->message( ev ).c_str() );
        return buffer;
    }
#if !defined(BOOST_NO_EXCEPTIONS)
    catch( ... )
    {
        detail::snprintf( buffer, len, "No message text available for error %d", ev );
        return buffer;
    }
#endif
}

} // namespace system
} // namespace boost

// interoperability with std::error_code, std::error_condition

#include <boost/system/detail/std_category_impl.hpp>
#include <boost/system/detail/mutex.hpp>
#include <new>

namespace boost
{
namespace system
{

// boost-module (M5 B'): init_stdcat() 与 operator std::error_category const& () const
// 的定义移入 src/boost_system_extras.cpp — 函数内 static (mutex / std_category 实例) 在
// gcc 模块管线消费者 TU 以强符号发射 → 多重定义; 移出头部后消费者只调用外部定义,
// 函数内 static 只在库 TU 单份存在 (语义不变)。

} // namespace system
} // namespace boost

#endif // #ifndef BOOST_SYSTEM_DETAIL_ERROR_CATEGORY_IMPL_HPP_INCLUDED
