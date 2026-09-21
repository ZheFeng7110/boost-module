// boost-example — profile feature demo: Boost.Log dump with the SSSE3/AVX2
// implementation compiled into the package (backend = "log-avx2").
//
// The consumer includes the upstream header directly (log is a compiled
// include-only library; macros never cross a module boundary) and links the
// package's log TUs. The profile selected at build time swaps the dump
// implementation; nothing here names a BOOST_LOG_USE_* macro.
#include <boost/log/utility/manipulators/dump.hpp>

#include <cstdio>
#include <sstream>
#include <string>

int main() {
    const std::string payload("boost-module profile backend-log-avx2");
    std::ostringstream os;
    os << boost::log::dump(payload.data(), payload.size());

    if (os.str().empty()) {
        std::puts("FAIL: empty dump output");
        return 1;
    }
    std::puts(os.str().c_str());
    return 0;
}
