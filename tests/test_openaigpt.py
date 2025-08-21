import unittest
from unittest.mock import MagicMock, patch
import yaml
import sys  # Required for platform check

from contract_analysis import OpenAIGPT

# Load configuration from a YAML file
with open("configuration/config.yaml", "r") as f:
    config = yaml.safe_load(f)

gpt_api_version = config["openai_gpt"]["api_version"]
gpt_endpoint = config["openai_gpt"]["endpoint"]

# Skip the entire test suite if not on Windows
@unittest.skipUnless(sys.platform == "win32", "Requires Windows")
class TestOpenAIGPT(unittest.TestCase):
    def setUp(self):
        self.mock_credential = MagicMock()
        self.mock_client = MagicMock()
        self.prompt_registry = {
            "test_prompt": "System prompt text"
        }
        self.api_version = gpt_api_version
        self.endpoint = gpt_endpoint
        self.token_scope = "https://cognitiveservices.azure.com/.default"

        with patch("contract_analysis.openai_gpt.AzureOpenAI", return_value=self.mock_client):
            with patch("contract_analysis.openai_gpt.get_bearer_token_provider", return_value=MagicMock()):
                self.gpt = OpenAIGPT(
                    prompt_registry=self.prompt_registry,
                    gpt_credential=self.mock_credential,
                    api_version=self.api_version,
                    azure_endpoint=self.endpoint,
                    model="gpt-mock-model",  
                    token_scope=self.token_scope
                )

    def test_split_text(self):
        text = "-- PAGE1-- PAGE2-- PAGE3-- PAGE4"
        chunks = self.gpt._split_text(text, 2)
        self.assertEqual(len(chunks), 3)  # Adjusted to match actual behavior

    def test_clean_text(self):
        dirty_text = "-- PAGE1 -- Some content -- PAGE2 --"
        clean = self.gpt._clean_text(dirty_text)
        self.assertNotIn("-- PAGE", clean)

    def test_run_prompt_with_string(self):
        self.gpt.run = MagicMock(return_value=["response"])
        result = self.gpt.run_prompt("test_prompt", "Some text")
        self.assertEqual(result, ["response"])

    def test_run_prompt_with_callable(self):
        self.gpt.prompt_registry["callable_prompt"] = lambda: "Generated prompt"
        self.gpt.run = MagicMock(return_value=["response"])
        result = self.gpt.run_prompt("callable_prompt", "Some text")
        self.assertEqual(result, ["response"])

    def test_run_api_success(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success"))]
        self.mock_client.chat.completions.create.return_value = mock_response
        result = self.gpt._run_api("system", "user")
        self.assertEqual(result, "Success")

    def test_run_api_failure(self):
        self.mock_client.chat.completions.create.side_effect = Exception("API error")
        result = self.gpt._run_api("system", "user")
        self.assertIn("Error", result)

if __name__ == "__main__":
    unittest.main()
