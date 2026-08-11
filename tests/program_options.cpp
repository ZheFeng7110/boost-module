// boost.program_options smoke — compiled lib linkage (parse/variables_map)
#include "test_assert.hpp"
import std;
import boost.program_options;

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

    po::options_description e("error");
    e.add_options()("port", po::value<int>());
    po::variables_map vm3;
    bool caught = false;
    try {
        po::store(po::command_line_parser({"--port=notanumber"}).options(e).run(), vm3);
        po::notify(vm3);
    } catch (po::invalid_option_value const&) {
        caught = true;
    }
    assert(caught);

    po::positional_options_description pos;
    pos.add("name", 1);
    assert(pos.max_total_count() == 1);

    std::vector<std::string> toks = po::split_unix("one \"two three\" four");
    assert(toks.size() == 3);
    assert(toks[1] == "two three");
    return 0;
}
