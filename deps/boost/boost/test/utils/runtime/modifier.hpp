//  (C) Copyright Gennadiy Rozental 2001.
//  Use, modification, and distribution are subject to the
//  Boost Software License, Version 1.0. (See accompanying file
//  LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)

//  See http://www.boost.org/libs/test for the library home page.
//
//  File        : $RCSfile$
//
//  Version     : $Revision$
//
//  Description : parameter modifiers
// ***************************************************************************

#ifndef BOOST_TEST_UTILS_RUNTIME_MODIFIER_HPP
#define BOOST_TEST_UTILS_RUNTIME_MODIFIER_HPP

// Boost.Test Runtime parameters
#include <boost/test/utils/runtime/fwd.hpp>

// Boost.Test
#include <boost/test/utils/named_params.hpp>
#include <boost/test/detail/global_typedef.hpp>

#include <boost/test/detail/suppress_warnings.hpp>


// New CLA API available only for some C++11 compilers
#if    !defined(BOOST_NO_CXX11_AUTO_DECLARATIONS) \
    && !defined(BOOST_NO_CXX11_TEMPLATE_ALIASES) \
    && !defined(BOOST_NO_CXX11_HDR_INITIALIZER_LIST) \
    && !defined(BOOST_NO_CXX11_UNIFIED_INITIALIZATION_SYNTAX)
#define BOOST_TEST_CLA_NEW_API
#endif

namespace boost {
namespace runtime {

// ************************************************************************** //
// **************         environment variable modifiers       ************** //
// ************************************************************************** //

// M11 vendored edit (gcc C++23 modules): the keyword objects lived in an
// anonymous namespace, which made them and their tag types TU-local; the
// test module surface hard-errors "exposes TU-local entity" when runtime
// templates (parameter.hpp, argument_factory.hpp, cla/parser.hpp) reference
// them. A named namespace with inline variables + a using-directive keeps
// the unqualified-lookup behavior. Replay after re-running import_boost
// (see M11 doc §6.9).
namespace runtime_detail {

#ifdef BOOST_TEST_CLA_NEW_API
inline auto const& description     = unit_test::static_constant<nfp::typed_keyword<cstring,struct description_t>>::value;
inline auto const& help            = unit_test::static_constant<nfp::typed_keyword<cstring,struct help_t>>::value;
inline auto const& env_var         = unit_test::static_constant<nfp::typed_keyword<cstring,struct env_var_t>>::value;
inline auto const& end_of_params   = unit_test::static_constant<nfp::typed_keyword<cstring,struct end_of_params_t>>::value;
inline auto const& negation_prefix = unit_test::static_constant<nfp::typed_keyword<cstring,struct neg_prefix_t>>::value;
inline auto const& value_hint      = unit_test::static_constant<nfp::typed_keyword<cstring,struct value_hint_t>>::value;
inline auto const& optional_value  = unit_test::static_constant<nfp::keyword<struct optional_value_t>>::value;
inline auto const& default_value   = unit_test::static_constant<nfp::keyword<struct default_value_t>>::value;
inline auto const& callback        = unit_test::static_constant<nfp::keyword<struct callback_t>>::value;

template<typename EnumType>
using enum_values = unit_test::static_constant<
  nfp::typed_keyword<std::initializer_list<std::pair<const cstring,EnumType>>, struct enum_values_t>
>;

#else

inline nfp::typed_keyword<cstring,struct description_t> description;
inline nfp::typed_keyword<cstring,struct help_t> help;
inline nfp::typed_keyword<cstring,struct env_var_t> env_var;
inline nfp::typed_keyword<cstring,struct end_of_params_t> end_of_params;
inline nfp::typed_keyword<cstring,struct neg_prefix_t> negation_prefix;
inline nfp::typed_keyword<cstring,struct value_hint_t> value_hint;
inline nfp::keyword<struct optional_value_t> optional_value;
inline nfp::keyword<struct default_value_t> default_value;
inline nfp::keyword<struct callback_t> callback;

template<typename EnumType>
struct enum_values_list {
    typedef std::pair<cstring,EnumType> ElemT;
    typedef std::vector<ElemT> ValuesT;

    enum_values_list const&
    operator()( cstring k, EnumType v ) const
    {
        const_cast<enum_values_list*>(this)->m_values.push_back( ElemT( k, v ) );

        return *this;
    }

    operator ValuesT const&() const { return m_values; }

private:
    ValuesT m_values;
};

template<typename EnumType>
struct enum_values : unit_test::static_constant<
  nfp::typed_keyword<enum_values_list<EnumType>, struct enum_values_t> >
{
};

#endif

} // namespace runtime_detail
using namespace runtime_detail;

} // namespace runtime
} // namespace boost

#include <boost/test/detail/enable_warnings.hpp>

#endif // BOOST_TEST_UTILS_RUNTIME_MODIFIER_HPP
