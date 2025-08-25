import platform  # ✅ Added for OS check
import sys
# Import necessary modules for testing and mocking
import unittest
from unittest.mock import MagicMock, patch

# Import the ContractAnalysis class to be tested
if sys.platform == "win32":
    from contract_analysis import ContractAnalysis

# ✅ This decorator ensures the test class runs only on Windows
@unittest.skipUnless(platform.system() == "Windows", "This test suite runs only on Windows")
class TestContractAnalysis(unittest.TestCase):

    def setUp(self):
        self.mock_document = MagicMock()
        self.mock_document.pdf_path_to_use = "mock_path.pdf"
        self.mock_document.ensure_pdf_exists = MagicMock()

        self.mock_translation = MagicMock()
        self.mock_document_intelligence = MagicMock()
        self.mock_content_understanding = MagicMock()
        self.mock_gpt = MagicMock()

        self.patcher_doc = patch('contract_analysis.contract_analysis.Document.from_file', return_value=self.mock_document)
        self.patcher_translation = patch('contract_analysis.contract_analysis.Translation', return_value=self.mock_translation)
        self.patcher_di = patch('contract_analysis.contract_analysis.DocumentIntelligence', return_value=self.mock_document_intelligence)
        self.patcher_cu = patch('contract_analysis.contract_analysis.ContentUnderstanding', return_value=self.mock_content_understanding)
        self.patcher_gpt = patch('contract_analysis.contract_analysis.OpenAIGPT', return_value=self.mock_gpt)

        self.patcher_doc.start()
        self.patcher_translation.start()
        self.patcher_di.start()
        self.patcher_cu.start()
        self.patcher_gpt.start()

        self.analysis = ContractAnalysis(
            document_path="test.docx",
            target_language="fr",
            translator_endpoint="https://translator.example.com",
            translator_region="westeurope",
            cu_endpoint="https://cu.example.com",
            cu_api_version="v1.0",
            cu_subscription_key="fake_key",
            cu_token_provider="fake_provider",
            cu_analyzer_id="analyzer_id",
            di_endpoint="https://di.example.com",
            di_model_id="model_id",
            gpt_api_version="v1.0",
            gpt_endpoint="https://gpt.example.com",
            gpt_model="gpt-mock-model"  
        )

    def tearDown(self):
        self.patcher_doc.stop()
        self.patcher_translation.stop()
        self.patcher_di.stop()
        self.patcher_cu.stop()
        self.patcher_gpt.stop()

    def test_document_initialization(self):
        self.mock_document.ensure_pdf_exists.assert_called_once()
        self.assertEqual(self.analysis.document, self.mock_document)

    def test_translation_initialization(self):
        self.assertEqual(self.analysis.translator, self.mock_translation)

    def test_document_intelligence_initialization(self):
        self.assertEqual(self.analysis.document_intelligence, self.mock_document_intelligence)

    def test_content_understanding_initialization(self):
        self.assertEqual(self.analysis.content_understanding, self.mock_content_understanding)

    def test_gpt_initialization(self):
        self.assertEqual(self.analysis.gpt, self.mock_gpt)

    def test_reset_gpt_credential(self):
        new_credential = MagicMock()
        self.analysis.reset_gpt_credential(
            new_credential,
            api_version="v2.0",
            azure_endpoint="https://newgpt.example.com",
            model="gpt-mock-model"
        )
        self.assertEqual(self.analysis.gpt_credential, new_credential)

    def test_document_layout_pages_property(self):
        self.mock_document_intelligence.document_layout_pages = ["page1", "page2"]
        self.assertEqual(self.analysis.document_layout_pages, ["page1", "page2"])

    def test_field_dict_property(self):
        self.mock_document_intelligence.field_dict = {"field1": "value1"}
        self.assertEqual(self.analysis.field_dict, {"field1": "value1"})

    def test_field_confidence_dict_property(self):
        self.mock_document_intelligence.field_confidence_dict = {"field1": 0.95}
        self.assertEqual(self.analysis.field_confidence_dict, {"field1": 0.95})

# Run the test suite
if __name__ == '__main__':
    unittest.main()