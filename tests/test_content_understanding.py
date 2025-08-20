# Import necessary modules for testing and mocking
import unittest
from unittest.mock import patch, MagicMock
import requests
from contract_analysis import ContentUnderstanding

# Load configuration from a YAML file
import yaml

# Read configuration values from the YAML file
with open("configuration/config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Extract specific configuration parameters for the ContentUnderstanding class
content_understanding_endpoint = config["content_understanding"]["endpoint"]
content_understanding_api_version = config["content_understanding"]["api_version"]
content_understanding_subscription_key = config["content_understanding"]["subscription_key"]
content_understanding_token_provider = config["content_understanding"]["token_provider"]
content_understanding_analyzer_id = config["content_understanding"]["analyzer_id"]

# Define the test case class for ContentUnderstanding
class TestContentUnderstanding(unittest.TestCase):

    # Setup method to initialize common test variables and the ContentUnderstanding instance
    def setUp(self):
        self.endpoint = content_understanding_endpoint
        self.api_version = content_understanding_api_version
        self.subscription_key = content_understanding_subscription_key
        self.token_provider = content_understanding_token_provider
        self.analyzer_id = content_understanding_analyzer_id
        self.x_ms_useragent = "cu-test-agent"

        # Create an instance of ContentUnderstanding with test configuration
        self.cu = ContentUnderstanding(
            endpoint=self.endpoint, 
            api_version=self.api_version,
            subscription_key=self.subscription_key,
            token_provider=None,
            analyzer_id=self.analyzer_id,
            x_ms_useragent=self.x_ms_useragent
        )
        self.cu.file_location = "contracts/document.pdf"

    # Test header generation using subscription key
    def test_get_headers_with_subscription_key(self):
        headers = self.cu._get_headers(self.subscription_key, None, self.x_ms_useragent)
        self.assertIn("Ocp-Apim-Subscription-Key", headers)
        self.assertEqual(headers["x-ms-useragent"], self.x_ms_useragent)

    # Test header generation using bearer token
    def test_get_headers_with_token(self):
        headers = self.cu._get_headers(None, "mock-token", self.x_ms_useragent)
        self.assertIn("Authorization", headers)
        self.assertEqual(headers["Authorization"], "Bearer mock-token")

    # Test begin_analyze method when file is provided locally
    @patch("contract_analysis.content_understanding.requests.post")
    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data=b"file-content")
    def test_begin_analyze_with_file(self, mock_file, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.cu.file_location = "contracts/document.pdf"
        response = self.cu.begin_analyze()
        mock_post.assert_called()
        self.assertEqual(response, mock_response)

    # Test begin_analyze method when file is provided as a URL
    @patch("contract_analysis.content_understanding.requests.post")
    def test_begin_analyze_with_url(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.cu.file_location = "https://example.com/document.pdf"
        response = self.cu.begin_analyze()
        mock_post.assert_called()
        self.assertEqual(response, mock_response)

    # Test polling result when analysis succeeds
    @patch("contract_analysis.content_understanding.requests.get")
    def test_poll_result_succeeded(self, mock_get):
        mock_response = MagicMock()
        mock_response.headers = {"operation-location": "https://mock.operation/location"}
        mock_result = {"status": "succeeded", "data": "mock-data"}
        mock_get.return_value.json.return_value = mock_result
        mock_get.return_value.raise_for_status.return_value = None

        result = self.cu.poll_result(mock_response, timeout_seconds=5, polling_interval_seconds=1)
        self.assertEqual(result, mock_result)

    # Test polling result when analysis fails
    @patch("contract_analysis.content_understanding.requests.get")
    def test_poll_result_failed(self, mock_get):
        mock_response = MagicMock()
        mock_response.headers = {"operation-location": "https://mock.operation/location"}
        mock_result = {"status": "failed"}
        mock_get.return_value.json.return_value = mock_result
        mock_get.return_value.raise_for_status.return_value = None

        with self.assertRaises(RuntimeError):
            self.cu.poll_result(mock_response, timeout_seconds=5, polling_interval_seconds=1)

    # Test polling result when operation-location header is missing
    def test_poll_result_missing_operation_location(self):
        mock_response = MagicMock()
        mock_response.headers = {}
        with self.assertRaises(ValueError):
            self.cu.poll_result(mock_response)

# Run the test suite
if __name__ == "__main__":
    unittest.main()
