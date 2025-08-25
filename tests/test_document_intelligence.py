import platform  # ✅ Added for OS check
import unittest
from unittest.mock import patch, MagicMock, mock_open
from azure.core.credentials import AzureKeyCredential
import sys
if sys.platform == "win32":
    from contract_analysis import DocumentIntelligence
import yaml

# ✅ This decorator ensures the test class runs only on Windows
@unittest.skipUnless(platform.system() == "Windows", "This test suite runs only on Windows")
class TestDocumentIntelligence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load configuration from YAML only once for all tests
        with open("configuration/config.yaml", "r") as f:
            config = yaml.safe_load(f)

        cls.document_intelligence_endpoint = config["document_intelligence"]["endpoint"]
        cls.document_intelligence_model_id = config["document_intelligence"]["model_id"]
        cls.prebuilt_layout_model_id = "prebuilt-layout"

    def setUp(self):
        self.mock_credential = MagicMock(spec=AzureKeyCredential)
        self.mock_endpoint = self.document_intelligence_endpoint
        self.mock_model_id = self.document_intelligence_model_id
        self.mock_pdf_path = "contracts/document.pdf"

        self.di = DocumentIntelligence(
            credential=self.mock_credential,
            di_endpoint=self.mock_endpoint,
            di_model_id=self.mock_model_id,
            document_pdf_path=self.mock_pdf_path
        )

    def test_init_field_dict(self):
        fields = ["Name", "Date"]
        self.di.init_field_dict(fields)
        self.assertEqual(self.di.field_dict, {"Name": None, "Date": None})
        self.assertEqual(self.di.field_confidence_dict, {"Name": 0.0, "Date": 0.0})

    @patch("contract_analysis.document_intelligence.DocumentAnalysisClient")
    def test_init_document_analysis_client(self, mock_client):
        self.di.init_document_analysis_client()
        mock_client.assert_called_with(endpoint=self.mock_endpoint, credential=self.mock_credential)
        self.assertIsNotNone(self.di.document_analysis_client)

    @patch("builtins.open", new_callable=mock_open, read_data=b"pdf-content")
    def test_analyse_document_layout(self, mock_file):
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_page = MagicMock()
        mock_line = MagicMock()
        mock_line.content = "Line 1"
        mock_page.lines = [mock_line]
        mock_result.pages = [mock_page]

        mock_client.begin_analyze_document.return_value.result.return_value = mock_result
        self.di.document_analysis_client = mock_client

        self.di.analyse_document_layout()
        mock_client.begin_analyze_document.assert_called_with(self.prebuilt_layout_model_id, b"pdf-content")
        self.assertEqual(self.di.document_layout_pages, ["Line 1"])

    @patch("builtins.open", new_callable=mock_open, read_data=b"pdf-content")
    def test_extract_document_fields(self, mock_file):
        self.di.init_field_dict(["Field1"])

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_doc = MagicMock()
        mock_field = MagicMock()
        mock_field.value = "Value1"
        mock_field.content = "Content1"
        mock_field.confidence = 0.95

        mock_doc.fields = {"Field1": mock_field}
        mock_result.documents = [mock_doc]
        mock_client.begin_analyze_document.return_value.result.return_value = mock_result
        self.di.document_analysis_client = mock_client

        self.di.extract_document_fields()
        mock_client.begin_analyze_document.assert_called_with(self.mock_model_id, b"pdf-content")
        self.assertEqual(self.di.field_dict["Field1"], "Value1")
        self.assertEqual(self.di.field_confidence_dict["Field1"], 0.95)

if __name__ == "__main__":
    unittest.main()