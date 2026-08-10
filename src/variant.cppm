// M3 final form (derived from the scripts/gen_exports.py draft; hand-finalized)
module;
#include <boost/variant.hpp>
#include <boost/variant/multivisitors.hpp>
#include <boost/variant/polymorphic_get.hpp>

export module boost.variant;

export import boost.core;
export import boost.type_traits;

#include "gen_exports/variant.inc"

