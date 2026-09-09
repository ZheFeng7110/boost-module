module;
#include <boost/version.hpp>

export module boost.version;

namespace boost_module::detail {
  inline constexpr int BOOST_VERSION_ = BOOST_VERSION;
  inline constexpr const char* BOOST_LIB_VERSION_ = BOOST_LIB_VERSION;
}

#undef BOOST_VERSION
#undef BOOST_LIB_VERSION

export namespace boost {
  inline constexpr int BOOST_VERSION = boost_module::detail::BOOST_VERSION_;
  inline constexpr const char* BOOST_LIB_VERSION = boost_module::detail::BOOST_LIB_VERSION_;
}
