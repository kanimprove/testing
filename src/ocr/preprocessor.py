"""OpenCV-based image preprocessing pipeline for OCR optimization.

Each step is a composable function. The `preprocess` function chains them
in the optimal order for scanned clinical documents (faxes, referrals, etc.).
"""

import numpy as np
import cv2


def load_image(path: str) -> np.ndarray:
    """Read an image file into a numpy array."""
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    return img


def convert_to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert to grayscale. Returns unchanged if already single-channel."""
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def denoise(img: np.ndarray) -> np.ndarray:
    """Remove noise using median blur — memory-efficient for scanned docs."""
    return cv2.medianBlur(img, 3)


def binarize(img: np.ndarray) -> np.ndarray:
    """Adaptive thresholding — handles uneven lighting common in faxes."""
    return cv2.adaptiveThreshold(
        img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )


def deskew(img: np.ndarray) -> np.ndarray:
    """Detect and correct skew angle using minAreaRect on contours.

    Uses a 4x downsampled image for angle detection to reduce memory usage,
    then applies the rotation to the full-size image.
    """
    # Downsample 4x for angle detection — reduces coordinate array by 16x
    small = img[::4, ::4]
    coords = np.column_stack(np.where(small < 255))
    del small
    if len(coords) < 5:
        return img
    angle = cv2.minAreaRect(coords)[-1]
    del coords
    # cv2.minAreaRect returns angles in [-90, 0)
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    # Only correct if skew is meaningful (> 0.5 degrees)
    if abs(angle) < 0.5:
        return img
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def preprocess(img: np.ndarray) -> np.ndarray:
    """Full preprocessing pipeline: grayscale → denoise → binarize → deskew.

    Explicitly deletes intermediate arrays to prevent memory accumulation
    when processing many pages in sequence.
    """
    gray = convert_to_grayscale(img)
    del img
    denoised = denoise(gray)
    del gray
    binary = binarize(denoised)
    del denoised
    result = deskew(binary)
    return result
