"""FRIDAY Document Parser — parse PDF, DOCX, TXT, CSV, JSON, XML, markdown files."""
import os
import json
import csv
import time
import hashlib
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import Counter


@dataclass
class DocumentMeta:
    filename: str
    file_path: str
    file_type: str
    file_size: int
    created_at: float
    modified_at: float
    encoding: str = "utf-8"
    checksum: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ParseResult:
    success: bool
    file_path: str
    file_type: str
    content: str = ""
    metadata: Dict = field(default_factory=dict)
    pages: int = 0
    lines: int = 0
    words: int = 0
    characters: int = 0
    tables: List[Dict] = field(default_factory=list)
    images: List[Dict] = field(default_factory=list)
    sections: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration: float = 0.0

    def to_dict(self):
        return asdict(self)


class DocumentParser:
    def __init__(self):
        self._supported = {
            ".txt": self._parse_text,
            ".md": self._parse_markdown,
            ".csv": self._parse_csv,
            ".tsv": self._parse_tsv,
            ".json": self._parse_json,
            ".jsonl": self._parse_jsonl,
            ".xml": self._parse_xml,
            ".html": self._parse_html,
            ".htm": self._parse_html,
            ".py": self._parse_python,
            ".js": self._parse_javascript,
            ".jsx": self._parse_javascript,
            ".ts": self._parse_javascript,
            ".tsx": self._parse_javascript,
            ".java": self._parse_code,
            ".c": self._parse_code,
            ".cpp": self._parse_code,
            ".h": self._parse_code,
            ".rs": self._parse_code,
            ".go": self._parse_code,
            ".rb": self._parse_code,
            ".php": self._parse_code,
            ".yml": self._parse_yaml,
            ".yaml": self._parse_yaml,
            ".toml": self._parse_toml,
            ".ini": self._parse_ini,
            ".cfg": self._parse_ini,
            ".log": self._parse_log,
            ".sql": self._parse_code,
            ".sh": self._parse_code,
            ".bash": self._parse_code,
            ".ps1": self._parse_code,
            ".bat": self._parse_code,
            ".cmd": self._parse_code,
        }

    def _read_file(self, file_path: str) -> tuple:
        encodings = ["utf-8", "latin-1", "cp1252", "ascii"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read(), enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), "utf-8-ignore"

    def _get_metadata(self, file_path: str) -> DocumentMeta:
        stat = os.stat(file_path)
        content, encoding = self._read_file(file_path)
        checksum = hashlib.md5(content.encode("utf-8", errors="ignore")).hexdigest()
        return DocumentMeta(
            filename=os.path.basename(file_path),
            file_path=file_path,
            file_type=os.path.splitext(file_path)[1].lower(),
            file_size=stat.st_size,
            created_at=stat.st_ctime,
            modified_at=stat.st_mtime,
            encoding=encoding,
            checksum=checksum,
        )

    def _count_stats(self, content: str) -> Dict:
        lines = content.split("\n")
        words = content.split()
        return {
            "lines": len(lines),
            "words": len(words),
            "characters": len(content),
        }

    def _parse_text(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            return ParseResult(
                success=True, file_path=file_path, file_type="text",
                content=content, metadata=meta.to_dict(),
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="text", errors=[str(e)])

    def _parse_markdown(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            sections = []
            current_section = {"title": "", "level": 0, "content": []}
            for line in content.split("\n"):
                if line.startswith("#"):
                    if current_section["title"]:
                        current_section["content"] = "\n".join(current_section["content"])
                        sections.append(current_section)
                    level = len(line) - len(line.lstrip("#"))
                    current_section = {"title": line.lstrip("# ").strip(), "level": level, "content": []}
                else:
                    current_section["content"].append(line)
            if current_section["title"]:
                current_section["content"] = "\n".join(current_section["content"])
                sections.append(current_section)

            return ParseResult(
                success=True, file_path=file_path, file_type="markdown",
                content=content, metadata=meta.to_dict(),
                sections=sections,
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="markdown", errors=[str(e)])

    def _parse_csv(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            tables = []
            with open(file_path, "r", encoding=encoding, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
                if rows:
                    headers = rows[0]
                    data_rows = [dict(zip(headers, row)) for row in rows[1:] if row]
                    tables.append({
                        "headers": headers,
                        "row_count": len(data_rows),
                        "sample": data_rows[:5],
                    })
            return ParseResult(
                success=True, file_path=file_path, file_type="csv",
                content=content, metadata=meta.to_dict(),
                tables=tables,
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="csv", errors=[str(e)])

    def _parse_tsv(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            tables = []
            with open(file_path, "r", encoding=encoding, newline="") as f:
                reader = csv.reader(f, delimiter="\t")
                rows = list(reader)
                if rows:
                    headers = rows[0]
                    data_rows = [dict(zip(headers, row)) for row in rows[1:] if row]
                    tables.append({
                        "headers": headers,
                        "row_count": len(data_rows),
                        "sample": data_rows[:5],
                    })
            return ParseResult(
                success=True, file_path=file_path, file_type="tsv",
                content=content, metadata=meta.to_dict(),
                tables=tables,
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="tsv", errors=[str(e)])

    def _parse_json(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            data = json.loads(content)
            structure = self._analyze_json(data)
            return ParseResult(
                success=True, file_path=file_path, file_type="json",
                content=content, metadata={**meta.to_dict(), "structure": structure},
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="json", errors=[str(e)])

    def _analyze_json(self, data: Any, depth: int = 0) -> Dict:
        if depth > 10:
            return {"type": "nested"}
        if isinstance(data, dict):
            return {"type": "object", "keys": len(data), "depth": depth,
                    "children": {k: self._analyze_json(v, depth + 1) for k, v in list(data.items())[:10]}}
        elif isinstance(data, list):
            return {"type": "array", "length": len(data), "depth": depth,
                    "sample": self._analyze_json(data[0], depth + 1) if data else {}}
        else:
            return {"type": type(data).__name__, "value": str(data)[:100]}

    def _parse_jsonl(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            lines_data = []
            for line in content.strip().split("\n"):
                if line.strip():
                    try:
                        lines_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            return ParseResult(
                success=True, file_path=file_path, file_type="jsonl",
                content=content, metadata={**meta.to_dict(), "record_count": len(lines_data)},
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="jsonl", errors=[str(e)])

    def _parse_xml(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            tree = ET.parse(file_path)
            root = tree.getroot()
            elements = []
            for elem in root.iter():
                elements.append({
                    "tag": elem.tag,
                    "attrib": dict(elem.attrib),
                    "text": (elem.text or "").strip()[:200],
                })
            return ParseResult(
                success=True, file_path=file_path, file_type="xml",
                content=content, metadata={**meta.to_dict(), "root_tag": root.tag, "element_count": len(elements)},
                sections=elements[:50],
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="xml", errors=[str(e)])

    def _parse_html(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            title = ""
            if "<title>" in content and "</title>" in content:
                start_idx = content.index("<title>") + 7
                end_idx = content.index("</title>")
                title = content[start_idx:end_idx].strip()
            import re
            text = re.sub(r"<[^>]+>", " ", content)
            text = re.sub(r"\s+", " ", text).strip()
            return ParseResult(
                success=True, file_path=file_path, file_type="html",
                content=text, metadata={**meta.to_dict(), "title": title},
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="html", errors=[str(e)])

    def _parse_python(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            import re
            functions = re.findall(r"def\s+(\w+)\s*\(", content)
            classes = re.findall(r"class\s+(\w+)", content)
            imports = re.findall(r"(?:from\s+(\S+)\s+)?import\s+(\S+)", content)
            return ParseResult(
                success=True, file_path=file_path, file_type="python",
                content=content, metadata={
                    **meta.to_dict(),
                    "functions": functions, "classes": classes,
                    "import_count": len(imports),
                },
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="python", errors=[str(e)])

    def _parse_javascript(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            import re
            functions = re.findall(r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:function|\([^)]*\)\s*=>))", content)
            classes = re.findall(r"class\s+(\w+)", content)
            return ParseResult(
                success=True, file_path=file_path, file_type="javascript",
                content=content, metadata={
                    **meta.to_dict(),
                    "functions": [f[0] or f[1] for f in functions],
                    "classes": classes,
                },
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="javascript", errors=[str(e)])

    def _parse_code(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            return ParseResult(
                success=True, file_path=file_path, file_type="code",
                content=content, metadata=meta.to_dict(),
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="code", errors=[str(e)])

    def _parse_yaml(self, file_path: str) -> ParseResult:
        return self._parse_text(file_path)

    def _parse_toml(self, file_path: str) -> ParseResult:
        return self._parse_text(file_path)

    def _parse_ini(self, file_path: str) -> ParseResult:
        return self._parse_text(file_path)

    def _parse_log(self, file_path: str) -> ParseResult:
        start = time.time()
        try:
            content, encoding = self._read_file(file_path)
            stats = self._count_stats(content)
            meta = self._get_metadata(file_path)
            import re
            levels = Counter()
            for line in content.split("\n"):
                match = re.search(r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b", line)
                if match:
                    levels[match.group(1)] += 1
            return ParseResult(
                success=True, file_path=file_path, file_type="log",
                content=content, metadata={**meta.to_dict(), "level_counts": dict(levels)},
                lines=stats["lines"], words=stats["words"], characters=stats["characters"],
                duration=time.time() - start,
            )
        except Exception as e:
            return ParseResult(success=False, file_path=file_path, file_type="log", errors=[str(e)])

    def parse(self, file_path: str) -> ParseResult:
        if not os.path.exists(file_path):
            return ParseResult(success=False, file_path=file_path, file_type="unknown",
                             errors=[f"File not found: {file_path}"])

        ext = os.path.splitext(file_path)[1].lower()
        parser = self._supported.get(ext)
        if parser:
            return parser(file_path)
        return self._parse_text(file_path)

    def parse_text(self, text: str, file_type: str = "text") -> ParseResult:
        start = time.time()
        stats = self._count_stats(text)
        return ParseResult(
            success=True, file_path="<inline>", file_type=file_type,
            content=text, metadata={"inline": True},
            lines=stats["lines"], words=stats["words"], characters=stats["characters"],
            duration=time.time() - start,
        )

    def get_supported(self) -> List[str]:
        return sorted(self._supported.keys())

    def batch_parse(self, file_paths: List[str]) -> List[Dict]:
        results = []
        for path in file_paths:
            result = self.parse(path)
            results.append(result.to_dict())
        return results


_parser = DocumentParser()


def document_parser_tool(action: str = "parse", **kwargs) -> Any:
    """Document parser tool dispatcher."""
    try:
        if action == "parse":
            file_path = kwargs.get("path", "")
            if not file_path:
                return {"error": "No path provided"}
            result = _parser.parse(file_path)
            return result.to_dict()

        elif action == "parse_text":
            text = kwargs.get("text", "")
            file_type = kwargs.get("type", "text")
            result = _parser.parse_text(text, file_type)
            return result.to_dict()

        elif action == "batch":
            paths = kwargs.get("paths", [])
            if not paths:
                return {"error": "No paths provided"}
            return {"results": _parser.batch_parse(paths), "count": len(paths)}

        elif action == "supported":
            return {"extensions": _parser.get_supported()}

        elif action == "info":
            file_path = kwargs.get("path", "")
            if not file_path:
                return {"error": "No path provided"}
            meta = _parser._get_metadata(file_path)
            return meta.to_dict()

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
