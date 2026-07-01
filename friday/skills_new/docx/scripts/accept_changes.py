"""
friday/skills/docx/scripts/accept_changes.py

Produces a clean copy of a .docx with all tracked changes accepted:
insertions are kept as normal text, deletions are removed entirely.

This does raw XML manipulation on word/document.xml since python-docx has
no native tracked-changes API.

Usage:
    python accept_changes.py in.docx out.docx
"""
import shutil
import sys
import zipfile
from pathlib import Path
from lxml import etree

NSMAP = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def accept_changes(in_path: str, out_path: str):
    shutil.copy(in_path, out_path)

    with zipfile.ZipFile(out_path, "r") as z:
        doc_xml = z.read("word/document.xml")
        all_names = z.namelist()
        other_files = {n: z.read(n) for n in all_names if n != "word/document.xml"}

    root = etree.fromstring(doc_xml)

    # Deletions: remove <w:del> nodes entirely (also removes nested delText)
    for del_node in root.findall(".//w:del", NSMAP):
        del_node.getparent().remove(del_node)

    # Insertions: unwrap <w:ins> — keep children, drop the wrapper element
    for ins_node in root.findall(".//w:ins", NSMAP):
        parent = ins_node.getparent()
        idx = list(parent).index(ins_node)
        for i, child in enumerate(list(ins_node)):
            parent.insert(idx + i, child)
        parent.remove(ins_node)

    new_doc_xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", new_doc_xml)
        for name, content in other_files.items():
            z.writestr(name, content)

    print(f"Accepted all tracked changes -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    accept_changes(sys.argv[1], sys.argv[2])
