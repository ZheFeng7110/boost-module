// M3 final form (derived from the scripts/gen_exports.py draft; hand-finalized)
module;
#include <boost/io/nullstream.hpp>
#include <boost/io/ostream_joiner.hpp>
// M11: ostream_put.hpp curated out of the io module GMF — its
// buffer_fill enum mismatches between the boost.io/boost.utility CMIs
// on gcc 16.1; consumers include the header themselves.
#include <boost/io/quoted.hpp>

export module boost.io;

#include "gen_exports/io.inc"

