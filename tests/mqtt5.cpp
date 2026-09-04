// boost.mqtt5 smoke — MQTT 5 protocol types (compile-time surface, no I/O)
// NB: the prop::xxx named constants are constexpr (internal-linkage) objects —
// not module-exportable; consumers spell the integral_constant form.
#include "test_assert.hpp"
import std;
import boost.mqtt5;

int main() {
    namespace m5 = boost::mqtt5;

    static_assert(m5::qos_e::at_most_once == m5::qos_e{0});
    static_assert(m5::qos_e::at_least_once == m5::qos_e{1});
    static_assert(m5::qos_e::exactly_once == m5::qos_e{2});

    using session_expiry =
        std::integral_constant<m5::prop::property_type,
                               m5::prop::property_type::session_expiry_interval_t>;
    m5::connect_props props;
    props[session_expiry{}] = std::optional<std::uint32_t>(60);
    assert(props[session_expiry{}] == std::optional<std::uint32_t>(60));

    static_assert(m5::log_level::error == m5::log_level{1});
    return 0;
}
