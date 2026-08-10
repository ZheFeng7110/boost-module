// M3 final form (derived from the scripts/gen_exports.py draft; hand-finalized)
// NB: string_regex.hpp is NOT in the GFM (replaced by the string.hpp
// aggregate): gcc 16.1.0 rejects the boost::regex v5 abi-tag surface inside a
// module interface ("mismatching abi tags for get_catalog_name_inst") even
// though the same headers compile standalone. The *regex family was pruned
// from gen_exports/algorithm.inc accordingly (clang keeps the full surface).
// Re-evaluated when boost.regex lands in M4.
module;
#include <boost/algorithm/algorithm.hpp>
#include <boost/algorithm/apply_permutation.hpp>
#include <boost/algorithm/clamp.hpp>
#include <boost/algorithm/cxx11/all_of.hpp>
#include <boost/algorithm/cxx11/any_of.hpp>
#include <boost/algorithm/cxx11/copy_if.hpp>
#include <boost/algorithm/cxx11/copy_n.hpp>
#include <boost/algorithm/cxx11/find_if_not.hpp>
#include <boost/algorithm/cxx11/iota.hpp>
#include <boost/algorithm/cxx11/is_partitioned.hpp>
#include <boost/algorithm/cxx11/is_sorted.hpp>
#include <boost/algorithm/cxx11/one_of.hpp>
#include <boost/algorithm/cxx11/partition_copy.hpp>
#include <boost/algorithm/cxx11/partition_point.hpp>
#include <boost/algorithm/cxx14/equal.hpp>
#include <boost/algorithm/cxx14/is_permutation.hpp>
#include <boost/algorithm/cxx17/exclusive_scan.hpp>
#include <boost/algorithm/cxx17/for_each_n.hpp>
#include <boost/algorithm/cxx17/inclusive_scan.hpp>
#include <boost/algorithm/cxx17/reduce.hpp>
#include <boost/algorithm/cxx17/transform_exclusive_scan.hpp>
#include <boost/algorithm/cxx17/transform_inclusive_scan.hpp>
#include <boost/algorithm/cxx17/transform_reduce.hpp>
#include <boost/algorithm/find_backward.hpp>
#include <boost/algorithm/find_not.hpp>
#include <boost/algorithm/gather.hpp>
#include <boost/algorithm/hex.hpp>
#include <boost/algorithm/is_clamped.hpp>
#include <boost/algorithm/is_palindrome.hpp>
#include <boost/algorithm/is_partitioned_until.hpp>
#include <boost/algorithm/minmax.hpp>
#include <boost/algorithm/minmax_element.hpp>
#include <boost/algorithm/searching/boyer_moore.hpp>
#include <boost/algorithm/searching/boyer_moore_horspool.hpp>
#include <boost/algorithm/searching/knuth_morris_pratt.hpp>
#include <boost/algorithm/sort_subrange.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/algorithm/string/trim_all.hpp>

export module boost.algorithm;

export import boost.core;
export import boost.iterator;
export import boost.range;
export import boost.tuple;
export import boost.type_traits;

#include "gen_exports/algorithm.inc"

