// boost.mqtt5 smoke — MQTT 5 protocol types (compile-time surface, no I/O)
// The prop::xxx named constants used to be constexpr (internal-linkage)
// objects; the vendored `inline constexpr` patch makes them external, so the
// module exports the named-constant spelling (no integral_constant workaround).
#include "test_assert.hpp"
import std;
import boost.mqtt5;

int main() {
    namespace m5 = boost::mqtt5;

    static_assert(m5::qos_e::at_most_once == m5::qos_e{0});
    static_assert(m5::qos_e::at_least_once == m5::qos_e{1});
    static_assert(m5::qos_e::exactly_once == m5::qos_e{2});

    using session_expiry_t =
        std::integral_constant<m5::prop::property_type,
                               m5::prop::property_type::session_expiry_interval_t>;
    static_assert(std::is_same_v<decltype(m5::prop::session_expiry_interval),
                                 const session_expiry_t>);

    m5::connect_props props;
    props[m5::prop::session_expiry_interval] = std::optional<std::uint32_t>(60);
    assert(props[m5::prop::session_expiry_interval] ==
           std::optional<std::uint32_t>(60));

    static_assert(m5::log_level::error == m5::log_level{1});
    static_assert(!m5::prop::name_v<
                  m5::prop::property_type::session_expiry_interval_t>.empty());

    // Variable-template instantiation coverage: the initializers of these
    // traits reference boost::is_detected (boost.type_traits), so using them
    // exercises the cross-module initializer edge (gen_exports A1).
    static_assert(!m5::has_at_resolve<m5::noop_logger>);
    static_assert(!m5::has_at_tcp_connect<m5::noop_logger>);
    return 0;
}
