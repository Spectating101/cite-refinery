"""Real Docling-on-PDF smoke plus imperfect cross-extractor numeric check.

This is NOT an accuracy certification. PyMuPDF is a second imperfect parser,
so shared numbers are only a diagnostic, not a ground-truth label.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from cite_refinery.external_engines import docling_extract


def run(pdf: Path) -> dict:
    import pymupdf
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions

    opts = PdfPipelineOptions()
    opts.do_ocr = False
    opts.do_table_structure = False
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)},
    )
    parsed = docling_extract(pdf, converter=converter)
    with pymupdf.open(pdf) as source:
        raw_text = "\n".join(page.get_text() for page in source)
        page_count = len(source)
    # Ignore isolated single-digit numbers; they are often table indices.
    number_pattern = re.compile(r"(?<!\w)\d[\d.,]{2,}(?!\w)")
    def numbers(text):
        return Counter(number_pattern.findall(text))
    reference = numbers(raw_text)
    extracted = numbers(parsed["content_markdown"])
    matched = sum((reference & extracted).values())
    reference_count = sum(reference.values())
    result = {
        "engine": "Docling 2.70.0", "stage": "actual_pdf_conversion",
        "source_sha256": parsed["sha256"],
        "pdf_pages": page_count,
        "docling_markdown_characters": parsed["characters"],
        "second_parser_characters": len(raw_text),
        "repeated_numeric_reference_tokens": reference_count,
        "numeric_tokens_found_both": matched,
        "numeric_overlap_recall_proxy": round(matched/reference_count, 3) if reference_count else None,
        "confirmed_real_runtime": True,
        "limits": [
            "PyMuPDF is NOT a reference transcript and tokens do not prove meaning.",
            "OCR and Docling advanced table-structure recognition disabled for this smoke.",
            "Numeric token overlap is not value alignment, row correctness or extraction accuracy.",
            "Do not promote extracted numbers to verified research claims.",
        ],
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--out",default="/tmp/cite-refinery-docling-pdf-quality.json")
    args = parser.parse_args()
    summary=run(Path(args.pdf))
    Path(args.out).write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print("REAL_DOCLING_QUALITY",json.dumps({
        k:v for k,v in summary.items() if k in (
            "pdf_pages", "docling_markdown_characters",
            "repeated_numeric_reference_tokens", "numeric_tokens_found_both",
            "numeric_overlap_recall_proxy")
    }))


if __name__=="__main__":
    main()
