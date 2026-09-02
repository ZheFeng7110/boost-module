// boost.log smoke — compiled lib linkage (core / record_ostream / text
// ostream backend / default sink TUs; BOOST_LOG_* macros stay include-side,
// M10 pattern)
#include "test_assert.hpp"
// include-only (T3 consumer rule, same as the exception face): importing
// boost.log makes gcc 16.1 emit two strong copies of the exported
// basic_formatting_ostream operator<< instantiations (one recorded in the
// log CMI from the module GMF, one instantiated in the consumer TU) and the
// assembler hard-errors "symbol ... already defined" on the same mangled
// name. The log module surface still compiles everywhere; the smoke test
// consumes the headers directly and keeps validating the compiled-lib
// linkage.
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
