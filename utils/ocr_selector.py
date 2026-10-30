
import cv2
import numpy as np


def select_psm(image):
    """
    Select a Tesseract PSM using basic image-layout features.
    This is a heuristic, not a trained classifier.
    """

    gray = cv2.cvtColor(
        np.array(image.convert("RGB")),
        cv2.COLOR_RGB2GRAY
    )

    # Binarise the image
    _, binary = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    height, width = binary.shape

    # Detect horizontal and vertical lines
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (max(20, width // 20), 1)
    )
    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (1, max(20, height // 20))
    )

    horizontal = cv2.morphologyEx(
        binary, cv2.MORPH_OPEN, horizontal_kernel
    )
    vertical = cv2.morphologyEx(
        binary, cv2.MORPH_OPEN, vertical_kernel
    )

    horizontal_count = cv2.countNonZero(horizontal)
    vertical_count = cv2.countNonZero(vertical)

    # Basic layout decision
    if horizontal_count > width * 2 or vertical_count > height * 2:
        return 6, "Structured table or block"

    # Detect whether text is distributed across multiple regions
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    regions = [
        cv2.boundingRect(contour)
        for contour in contours
        if cv2.contourArea(contour) > 20
    ]

    print(
    f"Layout analysis: horizontal={horizontal_count}, "
    f"vertical={vertical_count}, regions={len(regions)}"
    )
    if len(regions) > 100:
        return 11, "Scattered text"

    # Default fallback
    return 3, "Automatic page layout"
