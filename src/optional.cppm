// M3 final form (derived from the scripts/gen_exports.py draft; hand-finalized)
module;
#include <boost/optional.hpp>
#include <boost/optional/optional_io.hpp>

export module boost.optional;

export import boost.core;
export import boost.type_traits;

#include "gen_exports/optional.inc"

