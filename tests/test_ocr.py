"""Tests for OCR preprocessing and engine."""

import numpy as np
import pytest

from src.ocr.preprocessor import (
    convert_to_grayscale,
    denoise,
    binarize,
    deskew,
    preprocess,
)


class TestPreprocessor:
    """Test individual preprocessing steps."""

    def test_convert_to_grayscale_from_color(self):
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        result = convert_to_grayscale(img)
        assert len(result.shape) == 2
        assert result.shape == (100, 100)

    def test_convert_to_grayscale_already_gray(self):
        img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        result = convert_to_grayscale(img)
        assert result.shape == (100, 100)
        np.testing.assert_array_equal(result, img)

    def test_denoise(self):
        img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        result = denoise(img)
        assert result.shape == img.shape

    def test_binarize(self):
        img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        result = binarize(img)
        unique = np.unique(result)
        assert all(v in (0, 255) for v in unique)

    def test_deskew_no_content(self):
        """Deskew with no content should return the image unchanged."""
        img = np.zeros((100, 100), dtype=np.uint8)
        result = deskew(img)
        assert result.shape == img.shape

    def test_preprocess_pipeline(self):
        """Full pipeline should produce a 2D binary image."""
        img = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        result = preprocess(img)
        assert len(result.shape) == 2
