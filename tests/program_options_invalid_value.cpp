// Include-only coverage for invalid-value exceptions and option context.
#include "test_assert.hpp"
#include <boost/program_options.hpp>

#include <string>
#include <vector>

int main() {
    namespace po = boost::program_options;

    po::options_description desc("options");
    desc.add_options()("port", po::value<int>(), "port");

    po::variables_map vm;
    bool caught = false;
    try {
        po::store(po::command_line_parser(
                      std::vector<std::string>{"--port=notanumber"})
                      .options(desc).run(), vm);
    } catch (po::invalid_option_value const& e) {
        assert(e.get_option_name() == "--port");
        assert(std::string(e.what()).find("notanumber") != std::string::npos);
        caught = true;
    }
    assert(caught);
    return 0;
}
