from azure.identity import get_bearer_token_provider
from openai import AzureOpenAI
from typing import Callable, Union, List, Dict
import re
import time

PromptRegistry = Dict[str, Union[str, Callable[[], str]]]

class OpenAIGPT:
    """
    A robust and modular wrapper for Azure OpenAI GPT-4 API with prompt registry support.
    """

    def __init__(
        self,
        prompt_registry: PromptRegistry,
        gpt_credential,
        api_version: str,
        azure_endpoint: str,
        model: str,
        token_scope: str = "https://cognitiveservices.azure.com/.default"
    ):
        """
        Initialize the GPT client with a prompt registry and a custom Azure credential.

        Args:
            prompt_registry (PromptRegistry): Dictionary of prompts or prompt providers.
            gpt_credential: Azure credential object.
            api_version (str): API version for Azure OpenAI.
            azure_endpoint (str): Endpoint for Azure OpenAI.
            model (str): Deployment name of the GPT model.
            token_scope (str): Scope for Azure AD token.
        """
        self.gpt_credential = gpt_credential
        self.prompt_registry = prompt_registry
        self.client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            azure_ad_token_provider=get_bearer_token_provider(
                self.gpt_credential, token_scope
            )
        )
        self.model = model

    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """
        Splits text into chunks based on page markers.

        Args:
            text (str): Input text.
            chunk_size (int): Number of pages per chunk.

        Returns:
            List[str]: List of text chunks.
        """
        pages = text.split("-- PAGE")
        return [f"-- PAGE{''.join(pages[i:i+chunk_size])}" for i in range(0, len(pages), chunk_size)]

    def _clean_text(self, text: str) -> str:
        """
        Cleans text by removing page markers and metadata.

        Args:
            text (str): Input text.

        Returns:
            str: Cleaned text.
        """
        return re.sub(r'--.*?--', '', text, flags=re.DOTALL)

    def _run_api(self, system_prompt: str, user_prompt: str) -> str:
        """
        Executes a chat completion request with retry logic.

        Args:
            system_prompt (str): System-level prompt.
            user_prompt (str): User-level prompt.

        Returns:
            str: Response from the GPT model.
        """
        for attempt in range(5):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=3000,
                    top_p=0.5
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"[Retry {attempt+1}] OpenAI API error: {e}")
                time.sleep(2 ** attempt)
        return "Error: OpenAI API failed after retries."

    def run_prompt(self, prompt_key: str, text: str, clean: bool = False) -> List[str]:
        """
        Runs a prompt from the registry against the input text.

        Args:
            prompt_key (str): Key to retrieve the prompt.
            text (str): Input text.
            clean (bool): Whether to clean the text before processing.

        Returns:
            List[str]: List of GPT responses.

        Raises:
            ValueError: If the prompt key is not found.
        """
        if prompt_key not in self.prompt_registry:
            raise ValueError(f"Prompt '{prompt_key}' not found in registry.")
        prompt = self.prompt_registry[prompt_key]
        if callable(prompt):
            prompt = prompt()
        return self.run(text, prompt, clean=clean)

    def run(self, text: str, prompt: str, clean: bool = False) -> List[str]:
        """
        Runs the GPT model on the input text with fallback chunking.

        Args:
            text (str): Input text.
            prompt (str): Prompt to use.
            clean (bool): Whether to clean the text before processing.

        Returns:
            List[str]: List of GPT responses.
        """
        if clean:
            text = self._clean_text(text)

        try:
            return [self._run_api(prompt, text)]
        except Exception:
            print("Initial run failed, attempting fallback...")
            results = []
            for chunk in self._split_text(text, 4):
                try:
                    if clean:
                        chunk = self._clean_text(chunk)
                    results.append(self._run_api(prompt, chunk))
                except Exception:
                    for sub_chunk in self._split_text(chunk, 2):
                        try:
                            if clean:
                                sub_chunk = self._clean_text(sub_chunk)
                            results.append(self._run_api(prompt, sub_chunk))
                        except Exception as e:
                            print(f"Final fallback failed: {e}")
                            results.append("Error: Final fallback failed.")
            return results
