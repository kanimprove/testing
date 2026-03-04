"""Tesseract OCR engine with support for images and multi-page PDFs."""

import os

import numpy as np
import pytesseract
from PIL import Image

from src.ocr.preprocessor import load_image, preprocess


def ocr_image(image: np.ndarray, config: str = "--oem 3 --psm 6") -> str:
    """Run Tesseract OCR on a preprocessed image array.

    Args:
        image: Preprocessed image as numpy array.
        config: Tesseract config string. Default uses LSTM engine + block detection.

    Returns:
        Extracted text string.
    """
    pil_image = Image.fromarray(image)
    return pytesseract.image_to_string(pil_image, config=config).strip()


def ocr_pdf(pdf_path: str) -> str:
    """Convert PDF pages to images, preprocess, and OCR each page.

    Returns concatenated text with page markers.
    """
    from pdf2image import convert_from_path

    pages = convert_from_path(pdf_path, dpi=300)
    results = []
    for i, page in enumerate(pages, 1):
        img = np.array(page)
        img = preprocess(img)
        text = ocr_image(img)
        if text:
            results.append(f"--- Page {i} ---\n{text}")
    return "\n\n".join(results)


def ocr_file(file_path: str) -> str:
    """OCR a file, dispatching to PDF or image handler based on extension.

    Supported formats: .pdf, .png, .jpg, .jpeg, .tiff, .tif, .bmp

    Returns:
        Extracted text from the document.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file extension is not supported.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return ocr_pdf(file_path)

    if ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"):
        img = load_image(file_path)
        img = preprocess(img)
        return ocr_image(img)

    raise ValueError(f"Unsupported file format: {ext}")
