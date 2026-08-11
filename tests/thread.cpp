// boost.thread smoke — compiled lib linkage (thread/mutex/future, v2 API)
import std;
import boost.thread;

int main() {
    boost::mutex m;
    int shared = 0;
    {
        boost::lock_guard<boost::mutex> g(m);
        shared = 1;
    }
    if (shared != 1) return 1;

    boost::promise<int> p;
    boost::unique_future<int> f = p.get_future();
    boost::thread t([&p] {
        p.set_value(42);
    });
    if (f.wait_for(boost::chrono::seconds(10)) != boost::future_status::ready)
        return 2;
    if (f.get() != 42) return 3;
    t.join();

    boost::unique_future<int> g = boost::async(boost::launch::async, [] { return 7; });
    if (g.get() != 7) return 4;

    boost::unique_future<void> r = boost::make_ready_future();
    if (r.wait_for(boost::chrono::seconds(1)) != boost::future_status::ready)
        return 5;

    std::vector<boost::thread> pool;
    for (int i = 0; i < 4; ++i)
        pool.emplace_back([] { boost::this_thread::yield(); });
    for (auto& th : pool)
        th.join();

    boost::this_thread::sleep_for(boost::chrono::milliseconds(1));
    if (boost::this_thread::get_id() == boost::thread::id()) return 6;
    return 0;
}
