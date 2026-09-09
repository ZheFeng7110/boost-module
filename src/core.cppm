// M3 final form (derived from the scripts/gen_exports.py draft; hand-finalized).
//
// C5 (2026-09-09): BOOST_VERSION / BOOST_LIB_VERSION moved out of this module
// to a dedicated `boost.version` module (src/version.cppm — LIBS_SPECIAL tier
// in scripts/boost_common.py; no .inc, no .deps, hand-written TU that
// `#include <boost/version.hpp>` then `#undef`s the object macros and re-exposes
// them as `boost::BOOST_VERSION` / `boost::BOOST_LIB_VERSION` constexprs).
// Consumers wanting the same constants in their TU now `import boost.version;`
// (default feature set, §4.3 of the consolidated design doc). Macro-form
// consumers (`#if BOOST_VERSION >= 109100`) include <boost/version.hpp>
// directly — the upstream header is self-contained and no longer wrapped by
// this package.
module;
#include <boost/core/alloc_construct.hpp>
#include <boost/core/allocator_traits.hpp>
#include <boost/core/bit.hpp>
#include <boost/core/checked_delete.hpp>
#include <boost/core/cmath.hpp>
#include <boost/core/default_allocator.hpp>
#include <boost/core/empty_value.hpp>
#include <boost/core/exchange.hpp>
#include <boost/core/explicit_operator_bool.hpp>
#include <boost/core/fclose_deleter.hpp>
#include <boost/core/first_scalar.hpp>
#include <boost/core/functor.hpp>
#include <boost/core/identity.hpp>
#include <boost/core/ignore_unused.hpp>
#include <boost/core/is_same.hpp>
#include <boost/core/launder.hpp>
#include <boost/core/lightweight_test_trait.hpp>
#include <boost/core/make_span.hpp>
#include <boost/core/memory_resource.hpp>
#include <boost/core/no_exceptions_support.hpp>
#include <boost/core/noncopyable.hpp>
#include <boost/core/null_deleter.hpp>
#include <boost/core/pointer_in_range.hpp>
#include <boost/core/quick_exit.hpp>
#include <boost/core/ref.hpp>
#include <boost/core/scoped_enum.hpp>
#include <boost/core/serialization.hpp>
#include <boost/core/size.hpp>
#include <boost/core/snprintf.hpp>
#include <boost/core/swap.hpp>
#include <boost/core/typeinfo.hpp>
#include <boost/core/uncaught_exceptions.hpp>
#include <boost/core/underlying_type.hpp>
#include <boost/core/use_default.hpp>
#include <boost/core/verbose_terminate_handler.hpp>
#include <boost/core/yield_primitives.hpp>

export module boost.core;

#include "gen_exports/core.inc"

