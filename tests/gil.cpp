// boost.gil smoke — rgb8 image construction + view access
#include "test_assert.hpp"
import std;
import boost.gil;

int main() {
    namespace gil = boost::gil;

    gil::rgb8_image_t img(4, 3);
    assert(img.width() == 4);
    assert(img.height() == 3);

    auto view = gil::view(img);
    assert(view.width() == 4 && view.height() == 3);
    view(0, 0) = gil::rgb8_pixel_t(255, 128, 0);
    assert(gil::get_color(view(0, 0), gil::red_t()) == 255);
    assert(gil::get_color(view(0, 0), gil::green_t()) == 128);
    assert(gil::get_color(view(0, 0), gil::blue_t()) == 0);

    gil::gray8_image_t gray(2, 2, gil::gray8_pixel_t(7));
    assert(gil::view(gray)(1, 1) == gil::gray8_pixel_t(7));
    return 0;
}
