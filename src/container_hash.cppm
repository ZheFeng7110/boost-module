// M3 final form (derived from the scripts/gen_exports.py draft; hand-finalized)
module;
#include <boost/container_hash/extensions.hpp>
#include <boost/container_hash/is_tuple_like.hpp>

export module boost.container_hash;

export import boost.mp11;

#include "gen_exports/container_hash.inc"

