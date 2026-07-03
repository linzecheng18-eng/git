import unittest
from unittest.mock import Mock, patch

from PIL import Image

from core.image_utils import image_to_base64, validate_image_dimensions


class ImageUtilsTests(unittest.TestCase):
    def test_rejects_width_height_and_pixel_limits(self):
        for size in ((12001, 1), (1, 12001), (10000, 4001)):
            with self.subTest(size=size):
                image = Mock(size=size)
                with self.assertRaises(ValueError):
                    validate_image_dimensions(image)

    def test_image_conversion_checks_dimensions_before_convert(self):
        image = Mock(size=(12001, 1))
        context = Mock()
        context.__enter__ = Mock(return_value=image)
        context.__exit__ = Mock(return_value=False)
        with patch("core.image_utils.Image.open", return_value=context):
            with self.assertRaises(ValueError):
                image_to_base64(b"image")
        image.convert.assert_not_called()

    def test_decompression_bomb_warning_is_raised_as_error(self):
        with patch(
            "core.image_utils.Image.open",
            side_effect=Image.DecompressionBombWarning("large"),
        ):
            with self.assertRaises(Image.DecompressionBombWarning):
                image_to_base64(b"image")
