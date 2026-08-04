from pathlib import Path

from pypdf import PdfReader


class MultiFormatDocumentParser:
    def parse(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="replace")
        raise ValueError(f"Formato não suportado: {suffix}")
