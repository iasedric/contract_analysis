# Import necessary modules for testing and mocking
import unittest
from unittest.mock import patch, MagicMock
from contract_analysis.translation import Translation, TranslationAction
from contract_analysis.document import Document
from azure.core.credentials import TokenCredential
from pathlib import Path

# Load configuration from a YAML file
import yaml

# Read configuration values from the YAML file
with open("configuration/config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Extract specific configuration parameters for Translation
translator_endpoint = config["translator"]["endpoint"]
translator_region = config["translator"]["region"]

# Define a mock credential class for testing
class MockCredential(TokenCredential):
    def get_token(self, *args, **kwargs):
        class Token:
            token = "mock_token"
            expires_on = 9999999999
        return Token()

# Define the test case class for Translation
class TestTranslation(unittest.TestCase):

    # Setup method to initialize the Translation instance with mock configuration
    def setUp(self):
        self.mock_credential = MockCredential()
        self.mock_document = MagicMock(spec=Document)
        self.mock_document.extract_text.return_value = "Hello world"
        self.translator = Translation(
            credential=self.mock_credential,
            translator_endpoint=translator_endpoint,
            translator_region=translator_region,
            target_language="fr",
            document=self.mock_document
        )

    # Test translation of a single text string
    @patch("contract_analysis.translation.requests.post")
    def test_translate_text(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = [{"translations": [{"text": "Bonjour le monde"}]}]

        result = self.translator.translate_text("Hello world")
        self.assertEqual(result, "Bonjour le monde")

    # Test language detection functionality
    @patch("contract_analysis.translation.requests.post")
    def test_detect_language(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = [{"detectedLanguage": {"language": "en"}}]

        result = self.translator.translate_text(action=TranslationAction.DETECT)
        self.assertEqual(result, "en")

    # Test document translation workflow including paragraph extraction and saving
    @patch("contract_analysis.translation.requests.post")
    def test_translate_document(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = [{"translations": [{"text": "Bonjour"}]}]

        paragraph_mock = MagicMock()
        paragraph_mock.Range.Text.strip.return_value = "Hello"
        self.mock_document.get_paragraphs.return_value = [paragraph_mock]

        self.translator.translate_document()
        self.mock_document.save_translated.assert_called()
        self.mock_document.set_paths_to_use.assert_called_with(translated=True)

    # Test conditional translation based on detected language
    @patch("contract_analysis.translation.requests.post")
    def test_check_language_and_translate_if_needed(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.side_effect = [
            [{"detectedLanguage": {"language": "en"}}],
            [{"translations": [{"text": "Bonjour"}]}]
        ]

        paragraph_mock = MagicMock()
        paragraph_mock.Range.Text.strip.return_value = "Hello"
        self.mock_document.get_paragraphs.return_value = [paragraph_mock]

        self.translator.check_language_and_translate_if_needed()
        self.mock_document.save_translated.assert_called()
        self.mock_document.set_paths_to_use.assert_called_with(translated=True)

# Run the test suite
if __name__ == "__main__":
    unittest.main()
