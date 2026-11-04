
import cv2
import numpy as np
import re


def analyze_layout(image):
    """Measure basic page-layout features without assuming a report type."""

    gray = cv2.cvtColor(
        np.array(image.convert("RGB")),
        cv2.COLOR_RGB2GRAY
    )

    _, binary = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    height, width = binary.shape

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

    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    regions = [
        cv2.boundingRect(contour)
        for contour in contours
        if cv2.contourArea(contour) > 20
    ]

    return {
        "horizontal_count": horizontal_count,
        "vertical_count": vertical_count,
        "region_count": len(regions),
        "width": width,
        "height": height,
    }


def select_psm(image):
    """Suggest a PSM based on basic image-layout features."""

    features = analyze_layout(image)

    horizontal = features["horizontal_count"]
    vertical = features["vertical_count"]
    regions = features["region_count"]
    width = features["width"]
    height = features["height"]

    print(
        f"Layout analysis: horizontal={horizontal}, "
        f"vertical={vertical}, regions={regions}"
    )

    if horizontal > width * 2 or vertical > height * 2:
        return 6, "Possible structured table or block"

    if regions > 100:
        return 11, "Scattered text regions"

    return 3, "Automatic page layout"


def score_ocr_candidate(text, confidence):
    """
    Evaluate OCR text structure.
    This is a heuristic, not a medical interpretation.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return -100, {}

    numeric_pattern = re.compile(r"\d+(?:[.,]\d+)?")
    unit_pattern = re.compile(
        r"\b(?:mg/dl|g/dl|g/l|u/l|iu/l|mmol/l|umol/l|"
        r"seconds?|minutes?|%|fl|pg)\b",
        re.IGNORECASE
    )
    range_pattern = re.compile(
        r"\d+(?:[.,]\d+)?\s*(?:-|–|—|to)\s*"
        r"\d+(?:[.,]\d+)?",
        re.IGNORECASE
    )

    numeric_lines = sum(
        bool(numeric_pattern.search(line)) for line in lines
    )
    measurement_lines = sum(
        bool(numeric_pattern.search(line))
        and bool(unit_pattern.search(line))
        for line in lines
    )
    range_lines = sum(
        bool(range_pattern.search(line)) for line in lines
    )

    long_lines = sum(len(line) > 20 for line in lines)
    noise_lines = sum(
        len(line) <= 3 and not numeric_pattern.search(line)
        for line in lines
    )

    # Reward lines that keep measurements and their context together.
    score = (
        confidence * 0.5
        + measurement_lines * 5
        + range_lines * 3
        + numeric_lines * 0.5
        + min(long_lines, 20) * 0.5
        - noise_lines * 0.5
    )

    metrics = {
        "line_count": len(lines),
        "numeric_lines": numeric_lines,
        "measurement_lines": measurement_lines,
        "range_lines": range_lines,
        "noise_lines": noise_lines,
        "confidence": round(confidence, 2),
    }

    return score, metrics
