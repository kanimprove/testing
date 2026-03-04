"""CLI interface for the OCR + PHI de-identification pipeline.

Usage:
    python -m src.cli process <file_path> [--output-dir ./output]
    python -m src.cli process-all <input_dir> [--output-dir ./output]
    python -m src.cli reidentify <document_id> <deidentified_text_file> [--mapping-dir ./data/phi_mappings]
"""

import argparse
import glob
import os
import sys
import traceback

def _print(msg=""):
    """Print and flush immediately so output is visible before potential crashes."""
    print(msg)
    sys.stdout.flush()

SUPPORTED_EXTENSIONS = ("*.pdf", "*.png", "*.jpg", "*.jpeg", "*.tiff", "*.tif", "*.bmp")


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


def cmd_process_all(args):
    """Process all supported documents in a directory."""
    from src.pipeline import process_document
    from src.phi.mapping import MappingStore
    from src.phi.deidentifier import DeIdentifier

    os.makedirs(args.output_dir, exist_ok=True)
    mapping_store = MappingStore(storage_dir=args.mapping_dir)

    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(glob.glob(os.path.join(args.input_dir, ext)))

    if not files:
        _print(f"No supported documents found in: {args.input_dir}")
        _print(f"Supported formats: PDF, PNG, JPG, TIFF, BMP")
        _print(f"\nPut your scanned documents in the folder and try again.")
        return

    _print(f"Found {len(files)} document(s) to process.\n")

    deidentifier = DeIdentifier()
    success_count = 0
    fail_count = 0

    for i, file_path in enumerate(sorted(files), 1):
        filename = os.path.basename(file_path)
        _print(f"[{i}/{len(files)}] Processing: {filename}")
        try:
            result = process_document(
                file_path=file_path,
                mapping_store=mapping_store,
                deidentifier=deidentifier,
            )
            output_path = os.path.join(args.output_dir, f"{result.document_id}.txt")
            with open(output_path, "w") as f:
                f.write(result.deidentified_text)
            _print(f"        Document ID:       {result.document_id}")
            _print(f"        Pages processed:   {result.pages_processed}")
            _print(f"        PHI entities found: {result.phi_count}")
            _print(f"        Output: {output_path}")
            success_count += 1
        except Exception as e:
            _print(f"        ERROR: {e}")
            traceback.print_exc()
            sys.stdout.flush()
            fail_count += 1
        _print()

    _print(f"Done! {success_count} succeeded, {fail_count} failed out of {len(files)} document(s).")
    _print(f"Results are in: {os.path.abspath(args.output_dir)}")


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

    # process-all command
    proc_all = subparsers.add_parser("process-all", help="OCR and de-identify all documents in a folder")
    proc_all.add_argument("input_dir", help="Directory containing documents to process")
    proc_all.add_argument("--output-dir", default="./output", help="Directory for de-identified output")
    proc_all.add_argument("--mapping-dir", default="./data/phi_mappings", help="Directory for encrypted mappings")
    proc_all.set_defaults(func=cmd_process_all)

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
