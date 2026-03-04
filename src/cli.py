"""CLI interface for the OCR + PHI de-identification pipeline.

Usage:
    python -m src.cli process <file_path> [--output-dir ./output]
    python -m src.cli reidentify <document_id> <deidentified_text_file> [--mapping-dir ./data/phi_mappings]
"""

import argparse
import os
import sys


def cmd_process(args):
    """Run the full OCR → de-identification pipeline on a document."""
    from src.pipeline import process_document
    from src.phi.mapping import MappingStore

    os.makedirs(args.output_dir, exist_ok=True)

    mapping_store = MappingStore(storage_dir=args.mapping_dir)

    print(f"Processing: {args.file_path}")
    result = process_document(
        file_path=args.file_path,
        mapping_store=mapping_store,
    )

    # Save de-identified text
    output_path = os.path.join(args.output_dir, f"{result.document_id}.txt")
    with open(output_path, "w") as f:
        f.write(result.deidentified_text)

    print(f"\nDocument ID:      {result.document_id}")
    print(f"Original file:    {result.original_filename}")
    print(f"Pages processed:  {result.pages_processed}")
    print(f"PHI entities found: {result.phi_count}")
    print(f"De-identified text: {output_path}")
    if result.phi_count > 0:
        print(f"Encrypted mapping: {args.mapping_dir}/{result.document_id}.enc")

    return result


def cmd_reidentify(args):
    """Re-identify a previously de-identified document."""
    from src.phi.mapping import MappingStore

    mapping_store = MappingStore(storage_dir=args.mapping_dir)

    with open(args.text_file, "r") as f:
        deidentified_text = f.read()

    reidentified = mapping_store.reidentify(deidentified_text, args.document_id)

    if args.output:
        with open(args.output, "w") as f:
            f.write(reidentified)
        print(f"Re-identified text written to: {args.output}")
    else:
        print(reidentified)


def main():
    parser = argparse.ArgumentParser(
        prog="phi-pipeline",
        description="OCR + PHI De-Identification Pipeline for Clinical Documents",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # process command
    proc = subparsers.add_parser("process", help="OCR and de-identify a document")
    proc.add_argument("file_path", help="Path to input file (PDF, PNG, JPG, TIFF, BMP)")
    proc.add_argument("--output-dir", default="./output", help="Directory for de-identified output")
    proc.add_argument("--mapping-dir", default="./data/phi_mappings", help="Directory for encrypted mappings")
    proc.set_defaults(func=cmd_process)

    # reidentify command
    reid = subparsers.add_parser("reidentify", help="Re-identify a de-identified document")
    reid.add_argument("document_id", help="Document ID from processing")
    reid.add_argument("text_file", help="Path to de-identified text file")
    reid.add_argument("--mapping-dir", default="./data/phi_mappings", help="Directory for encrypted mappings")
    reid.add_argument("--output", "-o", help="Output file path (prints to stdout if not set)")
    reid.set_defaults(func=cmd_reidentify)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
