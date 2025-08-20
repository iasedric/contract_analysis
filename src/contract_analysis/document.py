import os
import win32com.client
from pathlib import Path
from typing import Optional


class Document:
    def __init__(self, docx_path: Path):
        if not docx_path.exists() or docx_path.suffix.lower() != ".docx":
            raise ValueError("Document must be a valid .docx file")

        self.folder = docx_path.parent
        self.base_name = docx_path.stem

        # Original paths
        self.original_docx_path = docx_path
        self.original_pdf_path = self.folder / f"{self.base_name}.pdf"

        # Translated paths
        self.translated_docx_path = self.folder / f"{self.base_name}_translated.docx"
        self.translated_pdf_path = self.folder / f"{self.base_name}_translated.pdf"

        # Final paths to use (set by Translation)
        self.docx_path_to_use: Optional[Path] = None
        self.pdf_path_to_use: Optional[Path] = None

        self.word_app: Optional[object] = None
        self.doc: Optional[object] = None

    @classmethod
    def from_file(cls, file_path: Path) -> "Document":
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.suffix.lower() == ".docx":
            return cls(file_path)

        elif file_path.suffix.lower() == ".pdf":
            docx_path = cls.convert_pdf_to_docx(file_path)
            return cls(docx_path)

        else:
            raise ValueError("Unsupported file type. Only .docx or .pdf are allowed.")

    @staticmethod
    def convert_pdf_to_docx(pdf_path: Path) -> Path:
        if not pdf_path.exists():
            raise FileNotFoundError("PDF file does not exist.")

        word_app = win32com.client.Dispatch("Word.Application")
        word_app.Visible = False

        try:
            doc = word_app.Documents.Open(str(pdf_path))
            docx_path = pdf_path.with_suffix(".docx")
            doc.SaveAs(str(docx_path), FileFormat=16)  # DOCX
            doc.Close(False)
        finally:
            word_app.Quit(SaveChanges=False)

        return docx_path

    @staticmethod
    def convert_docx_to_pdf(docx_path: Path) -> Path:
        if not docx_path.exists():
            raise FileNotFoundError("DOCX file does not exist.")

        word_app = win32com.client.Dispatch("Word.Application")
        word_app.Visible = False

        try:
            doc = word_app.Documents.Open(str(docx_path))
            pdf_path = docx_path.with_suffix(".pdf")
            doc.SaveAs(str(pdf_path), FileFormat=17)  # PDF
            doc.Close(False)
        finally:
            word_app.Quit(SaveChanges=False)

        return pdf_path

    def ensure_pdf_exists(self):
        if not self.original_pdf_path.exists():
            self.original_pdf_path = self.convert_docx_to_pdf(self.original_docx_path)

    def extract_text(self) -> str:
        self._open()
        try:
            return self.doc.Content.Text.strip()
        finally:
            self._close()

    def get_paragraphs(self):
        self._open()
        return list(self.doc.Paragraphs)

    def save_translated(self, translated_texts: list):
        self._open()
        try:
            paragraphs = list(self.doc.Paragraphs)
            for i, paragraph in enumerate(paragraphs):
                try:
                    text = translated_texts[i]
                    if paragraph.Range.Tables.Count > 0:
                        paragraph.Range.Text = text
                    else:
                        paragraph.Range.Text = text + "\r"
                except Exception:
                    continue

            self.doc.SaveAs(str(self.translated_docx_path), FileFormat=16)  # DOCX
            self.doc.SaveAs(str(self.translated_pdf_path), FileFormat=17)  # PDF

        finally:
            self._close()

    def set_paths_to_use(self, translated: bool):
        """
        Sets the final paths to use based on whether translation was performed.
        """
        if translated:
            self.docx_path_to_use = self.translated_docx_path
            self.pdf_path_to_use = self.translated_pdf_path
        else:
            self.docx_path_to_use = self.original_docx_path
            self.pdf_path_to_use = self.original_pdf_path

    def _open(self):
        if not self.word_app:
            self.word_app = win32com.client.Dispatch("Word.Application")
            self.word_app.Visible = False
        if not self.doc:
            self.doc = self.word_app.Documents.Open(str(self.original_docx_path))

    def _close(self):
        if self.doc:
            self.doc.Close(False)
            self.doc = None
        if self.word_app:
            self.word_app.Quit(False)
            self.word_app = None
