// boost.log smoke — compiled include-only (C1 downgrade, 2026-09-06: the
// module is gone but the feature stays; the library TUs still ship and link).
// Consumers #include the upstream headers and get the compiled-lib linkage
// from the feature's TU set (core / record_ostream / text ostream backend /
// default sink TUs); BOOST_LOG_* macros stay include-side, M10 pattern.
// (Even before the downgrade the gcc consumer face was unusable — the
// exported basic_formatting_ostream operator<< instantiations collided with
// the consumer's own, M11 §7.4 — so this test was already pure include; the
// downgrade removes the three-compiler consumption mismatch.)
#include "test_assert.hpp"
#include <boost/log/core/record.hpp>
#include <boost/log/core/core.hpp>
#include <boost/log/expressions.hpp>
#include <boost/log/sinks.hpp>
#include <boost/log/sources/logger.hpp>
#include <boost/log/sources/record_ostream.hpp>

int main() {
    // explicit core / sink pipeline writing into an ostringstream
    boost::shared_ptr<boost::log::sinks::text_ostream_backend> backend =
        boost::make_shared<boost::log::sinks::text_ostream_backend>();
    boost::shared_ptr<std::ostringstream> stream =
        boost::make_shared<std::ostringstream>();
    backend->add_stream(stream);
    boost::shared_ptr<boost::log::sinks::synchronous_sink<
        boost::log::sinks::text_ostream_backend>> sink =
        boost::make_shared<boost::log::sinks::synchronous_sink<
            boost::log::sinks::text_ostream_backend>>(backend);
    sink->set_formatter(boost::log::expressions::stream
                        << boost::log::expressions::message);
    boost::log::core::get()->add_sink(sink);

    boost::log::sources::logger lg;
    boost::log::record rec = lg.open_record();
    assert(rec);  // record convertible to bool
    if (rec) {
        boost::log::record_ostream os(rec);
        os << "smoke message";
        os.flush();
        // raw-record flow: the pump inside the macros does this on destruction;
        // with a bare record_ostream the user pushes explicitly.
        boost::log::core::get()->push_record(std::move(rec));
    }

    boost::log::core::get()->flush();
    boost::log::core::get()->remove_sink(sink);
    sink.reset();

    assert(stream->str().find("smoke message") != std::string::npos);
    return 0;
}
