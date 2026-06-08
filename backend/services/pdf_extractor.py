import fitz  # PyMuPDF


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts all text from a PDF file.
    
    Args:
        file_bytes: Raw PDF bytes from the uploaded file
        
    Returns:
        Plain text string of all pages combined
        
    Raises:
        ValueError: If file is not a valid PDF or text extraction fails
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        if doc.page_count == 0:
            raise ValueError("PDF has no pages.")

        text = ""
        for page in doc:
            text += page.get_text()

        doc.close()

        # Clean up extra whitespace
        text = "\n".join(
            line.strip()
            for line in text.splitlines()
            if line.strip()
        )

        if not text:
            raise ValueError("No text found in PDF. It may be a scanned image.")

        return text

    except Exception as e:
        raise ValueError(f"PDF extraction failed: {str(e)}")