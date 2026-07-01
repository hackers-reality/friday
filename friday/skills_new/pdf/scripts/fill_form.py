"""
friday/skills/pdf/scripts/fill_form.py

CLI helper for PDF AcroForms:
  - list mode: prints all field names/types/current values in a PDF form
  - fill mode: fills fields from a JSON file {"field_name": "value", ...}

Usage:
    python fill_form.py list form.pdf
    python fill_form.py fill form.pdf values.json filled.pdf
"""
import json
import sys

from pypdf import PdfReader, PdfWriter


def list_fields(pdf_path: str):
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    if not fields:
        print("No fillable form fields found. This PDF is likely flat/scanned — "
              "see SKILL.md section 5 for the coordinate-overlay approach instead.")
        return
    for name, f in fields.items():
        ftype = f.get("/FT", "?")
        current = f.get("/V", "")
        states = f.get("/_States_", None)
        line = f"  {name:<30} type={ftype} current={current!r}"
        if states:
            line += f" allowed_states={states}"
        print(line)


def fill_form(pdf_path: str, values_json_path: str, output_path: str):
    with open(values_json_path, "r", encoding="utf-8") as f:
        values = json.load(f)

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.append(reader)

    for page in writer.pages:
        writer.update_page_form_field_values(page, values, auto_regenerate=False)

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"Filled {len(values)} field(s) -> {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "list":
        list_fields(sys.argv[2])
    elif mode == "fill":
        if len(sys.argv) != 5:
            print("Usage: python fill_form.py fill form.pdf values.json filled.pdf")
            sys.exit(1)
        fill_form(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(f"Unknown mode: {mode}. Use 'list' or 'fill'.")
        sys.exit(1)
