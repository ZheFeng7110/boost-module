// boost.container_hash smoke — hash_combine, hash_value, hash container
import std;
import boost.container_hash;

int main() {
    std::size_t h = 0;
    boost::hash_combine(h, 42);
    boost::hash_combine(h, std::string("x"));
    std::size_t h2 = 0;
    boost::hash_combine(h2, 42);
    boost::hash_combine(h2, std::string("x"));
    if (h != h2 || h == 0) return 1;
    if (boost::hash_value(123) == 0) return 2;
    std::vector<int> v{1, 2, 3};
    if (boost::hash_value(v) == 0) return 3;
    std::pair<int, int> p{1, 2};
    if (boost::hash_value(p) == 0) return 4;
    std::array<int, 2> arr{4, 5};
    if (boost::hash_value(arr) == 0) return 5;
    return 0;
}
