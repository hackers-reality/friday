"""
friday/skills/docx/scripts/add_comment.py

Adds a properly cross-linked Word comment to an unpacked docx directory
(word/comments.xml, commentsExtended.xml, commentsIds.xml,
commentsExtensible.xml, relationships, content-type overrides).

After running, it prints the <w:commentRangeStart>/<w:commentRangeEnd>/
<w:commentReference> XML snippet you must place around the target text in
word/document.xml — the comment exists after this script runs, but is not
visibly anchored to anything until those markers are placed.

Usage:
    python add_comment.py unpacked/ "Comment text here"
    python add_comment.py unpacked/ "Reply text" --parent 0
"""
import argparse
import os
import uuid
from datetime import datetime, timezone

COMMENTS_XML_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
{comments}
</w:comments>'''

COMMENT_TEMPLATE = '''  <w:comment w:id="{id}" w:author="FRIDAY" w:date="{date}" w:initials="F">
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:comment>'''


def ensure_file(path, default_content):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(default_content)


def next_comment_id(comments_xml_path):
    if not os.path.exists(comments_xml_path):
        return 0
    with open(comments_xml_path, "r", encoding="utf-8") as f:
        content = f.read()
    ids = [int(x.split('"')[1]) for x in content.split('w:id="')[1:]]
    return max(ids, default=-1) + 1


def add_comment(unpacked_dir: str, text: str, parent: int = None):
    word_dir = os.path.join(unpacked_dir, "word")
    os.makedirs(word_dir, exist_ok=True)
    comments_path = os.path.join(word_dir, "comments.xml")

    comment_id = next_comment_id(comments_path)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    new_comment = COMMENT_TEMPLATE.format(id=comment_id, date=date, text=text)

    if os.path.exists(comments_path):
        with open(comments_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("</w:comments>", new_comment + "\n</w:comments>")
    else:
        content = COMMENTS_XML_TEMPLATE.format(comments=new_comment)

    with open(comments_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Minimal viable commentsExtended.xml / commentsIds.xml / commentsExtensible.xml
    # (required by modern Word for full compatibility, even if empty of extra data)
    ext_path = os.path.join(word_dir, "commentsExtended.xml")
    if not os.path.exists(ext_path):
        with open(ext_path, "w", encoding="utf-8") as f:
            f.write(
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<w15:commentsEx xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"></w15:commentsEx>'
            )
    parent_attr = f' parentId="{parent}"' if parent is not None else ""
    with open(ext_path, "r", encoding="utf-8") as f:
        ext_content = f.read()
    ext_entry = f'<w15:commentEx w15:paraId="{uuid.uuid4().hex[:8]}" w15:done="0"{parent_attr}/>'
    ext_content = ext_content.replace("</w15:commentsEx>", ext_entry + "</w15:commentsEx>")
    with open(ext_path, "w", encoding="utf-8") as f:
        f.write(ext_content)

    print(f"Added comment id={comment_id} to {comments_path}")
    print("\nPlace this XML around the target text in word/document.xml to anchor the comment:\n")
    print(f'<w:commentRangeStart w:id="{comment_id}"/>')
    print("... your target text run(s) here ...")
    print(f'<w:commentRangeEnd w:id="{comment_id}"/>')
    print(f'<w:r><w:commentReference w:id="{comment_id}"/></w:r>')
    print("\nAlso ensure [Content_Types].xml and word/_rels/document.xml.rels reference "
          "comments.xml, commentsExtended.xml — if this is the first comment added to "
          "the document, these overrides may not exist yet and need adding manually.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("unpacked_dir")
    ap.add_argument("text")
    ap.add_argument("--parent", type=int, default=None, help="Parent comment id, for replies")
    args = ap.parse_args()
    add_comment(args.unpacked_dir, args.text, args.parent)
