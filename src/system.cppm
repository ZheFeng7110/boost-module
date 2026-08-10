// M3 final form (derived from the scripts/gen_exports.py draft; hand-finalized)
module;
#include <boost/system.hpp>
#include <boost/system/is_error_code_enum.hpp>
#include <boost/system/is_error_condition_enum.hpp>
#include <boost/system/linux_error.hpp>
#include <boost/system/windows_error.hpp>

export module boost.system;

export import boost.mp11;
export import boost.variant2;

#include "gen_exports/system.inc"

