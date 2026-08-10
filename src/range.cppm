// M3 final form (derived from the scripts/gen_exports.py draft; hand-finalized)
module;
#include <boost/range.hpp>
#include <boost/range/adaptor/define_adaptor.hpp>
#include <boost/range/adaptor/ref_unwrapped.hpp>
#include <boost/range/adaptor/type_erased.hpp>
#include <boost/range/adaptors.hpp>
#include <boost/range/algorithm.hpp>
#include <boost/range/algorithm/swap_ranges.hpp>
#include <boost/range/algorithm_ext.hpp>
#include <boost/range/as_array.hpp>
#include <boost/range/as_literal.hpp>
#include <boost/range/combine.hpp>
#include <boost/range/const_reverse_iterator.hpp>
#include <boost/range/counting_range.hpp>
#include <boost/range/irange.hpp>
#include <boost/range/istream_range.hpp>
#include <boost/range/iterator_range_hash.hpp>
#include <boost/range/join.hpp>
#include <boost/range/numeric.hpp>
#include <boost/range/result_iterator.hpp>
#include <boost/range/reverse_result_iterator.hpp>

export module boost.range;

export import boost.core;
export import boost.iterator;
export import boost.optional;
export import boost.tuple;
export import boost.type_traits;

#include "gen_exports/range.inc"

