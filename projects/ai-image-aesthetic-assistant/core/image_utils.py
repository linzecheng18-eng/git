import base64
import io
import warnings

from PIL import Image

MAX_IMAGE_WIDTH = 12000
MAX_IMAGE_HEIGHT = 12000
MAX_IMAGE_PIXELS = 40_000_000


def validate_image_dimensions(image):
    width, height = image.size
    if (
        width > MAX_IMAGE_WIDTH
        or height > MAX_IMAGE_HEIGHT
        or width * height > MAX_IMAGE_PIXELS
    ):
        raise ValueError("image dimensions exceed limits")


def image_to_base64(image_bytes):
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(image_bytes)) as source:
            validate_image_dimensions(source)
            image = source.convert("RGB")
            image.thumbnail((1024, 1024))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=88)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
