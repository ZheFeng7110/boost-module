// boost-module (M5 B'): boost.system 互操作定义 (out-of-line)。
//
// 背景: gcc/mingw 模块管线在消费者 TU 以强符号 (非 COMDAT) 发射 inline 函数内的
// 局部 static — 与库 TU 的同一符号多重定义。boost.system 为纯头库, 无自有库 TU;
// 故将带函数内 static 的两个成员函数定义移入本 TU (单份存在):
//   - error_category::init_stdcat()                    (static mutex mx_)
//   - error_category::operator std::error_category&()  (static std_category 实例)
// 消费者与库 TU 只看到头文件里的声明, 一律外部调用 → 不再发射冲突符号。
// 对应头文件裁剪见 deps/boost/boost/system/detail/error_category_impl.hpp。
// 另: error_code::location() 的 static 改为头部命名空间级内部链接 constexpr
// (deps/boost/boost/system/detail/error_code.hpp), 无需本 TU。

#include <boost/system/error_code.hpp>
#include <boost/system/error_category.hpp>
#include <boost/system/detail/error_category_impl.hpp>

namespace boost
{
namespace system
{

void error_category::init_stdcat() const
{
    static_assert( sizeof( stdcat_ ) >= sizeof( boost::system::detail::std_category ), "sizeof(stdcat_) is not enough for std_category" );

#if defined(BOOST_MSVC) && BOOST_MSVC < 1900
    // no alignof
#else

    static_assert( alignof( decltype(stdcat_align_) ) >= alignof( boost::system::detail::std_category ), "alignof(stdcat_) is not enough for std_category" );

#endif

    // detail::mutex has a constexpr default constructor,
    // and therefore guarantees static initialization, on
    // everything except VS 2013 (msvc-12.0)

    static system::detail::mutex mx_;

    system::detail::lock_guard<system::detail::mutex> lk( mx_ );

    if( sc_init_.load( std::memory_order_acquire ) == 0 )
    {
        ::new( static_cast<void*>( stdcat_ ) ) boost::system::detail::std_category( this, system::detail::id_wrapper<0>() );
        sc_init_.store( 1, std::memory_order_release );
    }
}

BOOST_NOINLINE error_category::operator std::error_category const& () const
{
    if( id_ == detail::generic_category_id )
    {
// This condition must be the same as the one in error_condition.hpp
#if defined(BOOST_SYSTEM_AVOID_STD_GENERIC_CATEGORY)

        static const boost::system::detail::std_category generic_instance( this, system::detail::id_wrapper<0x1F4D3>() );
        return generic_instance;

#else

        return std::generic_category();

#endif
    }

    if( id_ == detail::system_category_id )
    {
// This condition must be the same as the one in error_code.hpp
#if defined(BOOST_SYSTEM_AVOID_STD_SYSTEM_CATEGORY)

        static const boost::system::detail::std_category system_instance( this, system::detail::id_wrapper<0x1F4D7>() );
        return system_instance;

#else

        return std::system_category();

#endif
    }

    if( sc_init_.load( std::memory_order_acquire ) == 0 )
    {
        init_stdcat();
    }

    return *static_cast<boost::system::detail::std_category const*>( static_cast<void const*>( stdcat_ ) );
}

} // namespace system
} // namespace boost
