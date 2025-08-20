# Import necessary modules for testing and mocking
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from contract_analysis import Document

# Define the test case class for Document
class TestDocument(unittest.TestCase):

    # Setup method to define sample file paths used in tests
    def setUp(self):
        self.sample_docx = Path("contracts/samples/sample.docx")
        self.sample_pdf = Path("contracts/samples/sample.pdf")

    # Test initialization with a valid DOCX path
    @patch("contract_analysis.document.Path.exists", return_value=True)
    def test_init_valid_docx(self, mock_exists):
        doc = Document(self.sample_docx)
        self.assertEqual(doc.original_docx_path, self.sample_docx)

    # Test initialization with an invalid path, expecting a ValueError
    @patch("contract_analysis.document.Path.exists", return_value=False)
    def test_init_invalid_path(self, mock_exists):
        with self.assertRaises(ValueError):
            Document(self.sample_docx)

    # Test the from_file method with a DOCX file
    @patch("contract_analysis.document.Path.exists", return_value=True)
    def test_from_file_docx(self, mock_exists):
        doc = Document.from_file(self.sample_docx)
        self.assertIsInstance(doc, Document)

    # Test the from_file method with a PDF file and mock conversion to DOCX
    @patch("contract_analysis.document.Document.convert_pdf_to_docx")
    @patch("contract_analysis.document.Path.exists", return_value=True)
    def test_from_file_pdf(self, mock_exists, mock_convert):
        mock_convert.return_value = self.sample_docx
        doc = Document.from_file(self.sample_pdf)
        self.assertIsInstance(doc, Document)

    # Test conversion from DOCX to PDF using mocked win32com client
    @patch("contract_analysis.document.win32com.client.Dispatch")
    @patch("contract_analysis.document.Path.exists", return_value=True)
    def test_convert_docx_to_pdf(self, mock_exists, mock_dispatch):
        mock_word = MagicMock()
        mock_doc = MagicMock()
        mock_dispatch.return_value = mock_word
        mock_word.Documents.Open.return_value = mock_doc

        result = Document.convert_docx_to_pdf(self.sample_docx)
        self.assertEqual(result, self.sample_docx.with_suffix(".pdf"))
        mock_doc.SaveAs.assert_called()
        mock_doc.Close.assert_called()
        mock_word.Quit.assert_called()

    # Test conversion from PDF to DOCX using mocked win32com client
    @patch("contract_analysis.document.win32com.client.Dispatch")
    @patch("contract_analysis.document.Path.exists", return_value=True)
    def test_convert_pdf_to_docx(self, mock_exists, mock_dispatch):
        mock_word = MagicMock()
        mock_doc = MagicMock()
        mock_dispatch.return_value = mock_word
        mock_word.Documents.Open.return_value = mock_doc

        result = Document.convert_pdf_to_docx(self.sample_pdf)
        self.assertEqual(result, self.sample_pdf.with_suffix(".docx"))
        mock_doc.SaveAs.assert_called()
        mock_doc.Close.assert_called()
        mock_word.Quit.assert_called()

# Run the test suite
if __name__ == '__main__':
    unittest.main()
