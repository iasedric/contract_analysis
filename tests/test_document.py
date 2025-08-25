import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Skip the entire test suite if not on Windows
@unittest.skipUnless(sys.platform == "win32", "Requires Windows")
class TestDocument(unittest.TestCase):
    def setUp(self):
        self.sample_docx = Path("contracts/samples/sample.docx")
        self.sample_pdf = Path("contracts/samples/sample.pdf")

    @patch("contract_analysis.document.Path.exists", return_value=True)
    def test_init_valid_docx(self, mock_exists):
        from contract_analysis import Document
        doc = Document(self.sample_docx)
        self.assertEqual(doc.original_docx_path, self.sample_docx)

    @patch("contract_analysis.document.Path.exists", return_value=False)
    def test_init_invalid_path(self, mock_exists):
        from contract_analysis import Document
        with self.assertRaises(ValueError):
            Document(self.sample_docx)

    @patch("contract_analysis.document.Path.exists", return_value=True)
    def test_from_file_docx(self, mock_exists):
        from contract_analysis import Document
        doc = Document.from_file(self.sample_docx)
        self.assertIsInstance(doc, Document)

    @patch("contract_analysis.document.Document.convert_pdf_to_docx")
    @patch("contract_analysis.document.Path.exists", return_value=True)
    def test_from_file_pdf(self, mock_exists, mock_convert):
        from contract_analysis import Document
        mock_convert.return_value = self.sample_docx
        doc = Document.from_file(self.sample_pdf)
        self.assertIsInstance(doc, Document)

    @patch("contract_analysis.document.win32com.client.Dispatch")
    @patch("contract_analysis.document.Path.exists", return_value=True)
    def test_convert_docx_to_pdf(self, mock_exists, mock_dispatch):
        from contract_analysis import Document
        mock_word = MagicMock()
        mock_doc = MagicMock()
        mock_dispatch.return_value = mock_word
        mock_word.Documents.Open.return_value = mock_doc

        result = Document.convert_docx_to_pdf(self.sample_docx)
        self.assertEqual(result, self.sample_docx.with_suffix(".pdf"))
        mock_doc.SaveAs.assert_called()
        mock_doc.Close.assert_called()
        mock_word.Quit.assert_called()

    @patch("contract_analysis.document.win32com.client.Dispatch")
    @patch("contract_analysis.document.Path.exists", return_value=True)
    def test_convert_pdf_to_docx(self, mock_exists, mock_dispatch):
        from contract_analysis import Document
        mock_word = MagicMock()
        mock_doc = MagicMock()
        mock_dispatch.return_value = mock_word
        mock_word.Documents.Open.return_value = mock_doc

        result = Document.convert_pdf_to_docx(self.sample_pdf)
        self.assertEqual(result, self.sample_pdf.with_suffix(".docx"))
        mock_doc.SaveAs.assert_called()
        mock_doc.Close.assert_called()
        mock_word.Quit.assert_called()

if __name__ == "__main__":
    unittest.main()