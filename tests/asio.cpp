// boost.asio smoke — io_context + steady_timer + post (no sockets, no winsock)
#include "test_assert.hpp"
import std;
import boost.asio;

int main() {
    namespace asio = boost::asio;
    asio::io_context io;
    bool ran = false;
    asio::post(io, [&] { ran = true; });

    asio::steady_timer timer(io, std::chrono::milliseconds(1));
    bool expired = false;
    timer.async_wait([&](const boost::system::error_code& ec) {
        assert(!ec);
        expired = true;
    });

    io.run();
    assert(ran);
    assert(expired);
    return 0;
}
