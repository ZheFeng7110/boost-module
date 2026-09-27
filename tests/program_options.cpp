// boost.program_options smoke — compiled lib linkage (parse/variables_map)
#include "test_assert.hpp"
import std;
import boost.program_options;

// Out-of-line bad-value helper — lives in a plain (include-only) lib TU
// (src/boost_program_options_extras.cpp); declared by hand here instead of
// through the module so the generated module surface stays untouched.
namespace boost { namespace program_options { namespace detail {
bool mcpp_rejects_invalid_option_value();
}}}

int main() {
    namespace po = boost::program_options;

    po::options_description desc("options");
    desc.add_options()
        ("help,h", "show help")
        ("port,p", po::value<int>()->default_value(8080), "port")
        ("name", po::value<std::string>(), "name")
        ("verbose,v", po::bool_switch(), "verbose");

    std::vector<std::string> args =
        po::split_unix("--port 9000 --name boost --verbose");

    po::variables_map vm;
    po::store(po::command_line_parser(args).options(desc).positional(
                  po::positional_options_description().add("name", -1))
                  .run(), vm);
    po::notify(vm);

    assert(vm["port"].as<int>() == 9000);
    assert(vm["name"].as<std::string>() == "boost");
    assert(vm["verbose"].as<bool>());
    assert(!vm.count("help"));

    po::variables_map vm2;
    po::store(po::command_line_parser({"--port", "1234"}).options(desc).run(), vm2);
    po::notify(vm2);
    assert(vm2["port"].as<int>() == 1234);

    // b1.92 macOS typeinfo/weak-copy regression: the bad-value throw+catch
    // lives in a plain include-only lib TU (src/boost_program_options_extras.cpp)
    // and the generated module surface suppresses this TU's implicit
    // instantiation of the throwing templates (typed_value<int,char> /
    // validate<int,char>, extern template in gen_exports/program_options.inc;
    // explicit instantiation in that lib TU). Before the suppression the
    // linker's first-wins weak coalescing picked this consumer TU's copy as
    // the actual throw site, where the exception aborted with
    // "terminating due to uncaught exception of type
    // boost::wrapexcept<invalid_option_value>" (exit 134, CI runs
    // 35872964147 / 36104518727 / 36317554695). See
    // .agents/docs/2026-09-25-macos-typeinfo-catch-regression.md.
    assert(po::detail::mcpp_rejects_invalid_option_value());

    po::positional_options_description pos;
    pos.add("name", 1);
    assert(pos.max_total_count() == 1);

    std::vector<std::string> toks = po::split_unix("one \"two three\" four");
    assert(toks.size() == 3);
    assert(toks[1] == "two three");
    return 0;
}
