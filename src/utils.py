from io import BytesIO
import base64
import json
import logging
import os
import random
import string
import secrets
from time import time
from typing import Any, Tuple, List

from PIL import Image
from profanity_check import predict
import requests

from config import config

chars = string.ascii_letters + string.digits


def gen_random(length=None):
    if length is None:
        length = config.DEFAULT_RANDOM_TEXT_LENGTH

    return "".join(secrets.choice(chars) for _ in range(length))


def is_image_file(obj: Any) -> bool:
    try:
        # Attempt to open the file as an image
        Image.open(obj)
        obj.seek(0)
        # Close the file after checking, to free up resources
        return True
    except IOError:
        # If PIL.Image.open() raises an IOError, the file is not an image
        return False


def resize_image(img: Any, new_size: Tuple[int, int] = (300, 300)) -> Any:
    """returns the resized image object"""
    # Open the image
    image = Image.open(img)

    # Resize the image while maintaining its aspect ratio
    image.thumbnail(new_size, Image.Resampling.LANCZOS)

    img_out = BytesIO()
    image.save(img_out, format=image.format)
    img_out.seek(0)
    return img_out


def resize_and_center_crop(img: Any, target_size: Tuple[int, int] = (450, 450)):
    # Open the image
    image = Image.open(img)

    # Resize the image while maintaining the aspect ratio
    image.thumbnail(target_size, Image.ANTIALIAS)

    # Calculate the center coordinates for cropping
    width, height = image.size
    left = (width - target_size[0]) / 2
    top = (height - target_size[1]) / 2
    right = (width + target_size[0]) / 2
    bottom = (height + target_size[1]) / 2

    # Perform the center cropping
    cropped_image = image.crop((left, top, right, bottom))

    img_out = BytesIO()
    cropped_image.save(img_out, format=image.format)
    img_out.seek(0)
    # Return the resized and cropped image
    return img_out


def is_explicit_content(img: Any) -> bool:
    b64_file = base64.b64encode(img.read()).decode("utf-8")
    data = {"foo": b64_file}
    img.seek(0)

    try:
        res = requests.post(config.NUDENET_CLASSIFIER_URL, json={"data": data})
        res.raise_for_status()
        data = res.json()
        """
        results look like
        {
            "prediction": {
                "img23.jpeg": {
                    "unsafe": 0.03973957896232605,
                    "safe": 0.9602603912353516
                }
            },
            "success": true
        }
        """
        return (
            data.get("prediction", {}).get("foo", {}).get("unsafe", 1)
            > config.EXPLICIT_IMAGE_THRESHOLD
        )

    except Exception as exp:
        logging.error(f"Could not classify image - {exp}")
        return True  # default is the image is explict


def scrub_explicit(string: str) -> str:
    res = str(string)
    for word in [x for x in string.split(" ") if x]:
        if predict([word]) == 1:
            res.replace(word, "*" * len(word))
    return res


def truncate_string(string: str, max_length: int) -> str:
    if len(string) < max_length:
        return string

    return string[0:max_length] + "..."
