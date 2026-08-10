// M3 final form (derived from the scripts/gen_exports.py draft; hand-finalized)
module;
#include <boost/scope/defer.hpp>
#include <boost/scope/error_code_checker.hpp>
#include <boost/scope/scope_fail.hpp>
#include <boost/scope/scope_success.hpp>
#include <boost/scope/unique_fd.hpp>

export module boost.scope;

// NB: no `export import boost.core;` — gcc 16.1.0 ICEs (Segmentation fault at
// the export-module line) when this GMF include set (which pulls
// unique_fd.hpp, whose entities depend on boost.core) is combined with
// re-exporting boost.core. scope.inc carries no boost::core:: entities (they
// are claimed by boost.core itself), so consumers import boost.core on their
// own. (Clang has no such issue; tracked as a gcc bug for M6 CI.)

#include "gen_exports/scope.inc"

