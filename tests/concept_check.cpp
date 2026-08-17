// boost.concept_check smoke — concept classes + function_requires
#include "test_assert.hpp"
import std;
import boost.concept_check;

int main() {
    boost::function_requires<boost::DefaultConstructibleConcept<int>>();
    boost::function_requires<boost::AssignableConcept<int>>();
    boost::function_requires<boost::CopyConstructibleConcept<int>>();
    boost::function_requires<boost::EqualityComparableConcept<int>>();
    boost::function_requires<boost::LessThanComparableConcept<int>>();
    boost::function_requires<boost::SignedIntegerConcept<int>>();
    boost::function_requires<boost::RandomAccessIteratorConcept<int*>>();
    boost::function_requires<boost::ForwardIteratorConcept<std::vector<int>::iterator>>();
    boost::function_requires<boost::BidirectionalIteratorConcept<std::list<int>::iterator>>();
    return 0;
}
