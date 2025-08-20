import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast
from dataclasses import dataclass

import requests


@dataclass(frozen=True, kw_only=True)
class Settings:
    endpoint: str
    api_version: str
    subscription_key: str | None = None
    aad_token: str | None = None

    def __post_init__(self):
        key_not_provided = (
            not self.subscription_key
            or self.subscription_key == "AZURE_CONTENT_UNDERSTANDING_SUBSCRIPTION_KEY"
        )
        token_not_provided = (
            not self.aad_token
            or self.aad_token == "AZURE_CONTENT_UNDERSTANDING_AAD_TOKEN"
        )
        if key_not_provided and token_not_provided:
            raise ValueError(
                "Either 'subscription_key' or 'aad_token' must be provided"
            )

    @property
    def token_provider(self) -> Callable[[], str] | None:
        """
        Returns a callable that provides the AAD token if available.

        Returns:
            Callable[[], str] | None: A function returning the AAD token or None.
        """
        aad_token = self.aad_token
        if aad_token is None:
            return None

        return lambda: aad_token


class ContentUnderstanding:
    def __init__(
        self,
        endpoint: str,
        api_version: str,
        subscription_key: str | None = None,
        token_provider: Callable[[], str] | None = None,
        analyzer_id: str | None = None,
        x_ms_useragent: str = "cu-sample-code",
    ) -> None:
        """
        Initializes the ContentUnderstanding client with required credentials and configuration.

        Args:
            endpoint (str): The base URL of the Content Understanding service.
            api_version (str): The API version to use.
            subscription_key (str, optional): The subscription key for authentication.
            token_provider (Callable, optional): A callable that returns an AAD token.
            analyzer_id (str, optional): The ID of the analyzer to use.
            x_ms_useragent (str): Custom user agent string for tracking.
        """
        if not subscription_key and token_provider is None:
            raise ValueError(
                "Either subscription key or token provider must be provided"
            )
        if not api_version:
            raise ValueError("API version must be provided")
        if not endpoint:
            raise ValueError("Endpoint must be provided")

        self.endpoint: str = endpoint.rstrip("/")
        self.api_version: str = api_version
        self.analyzer_id: str | None = analyzer_id
        self.file_location: str = None
        self._logger: logging.Logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.INFO)
        self._headers: dict[str, str] = self._get_headers(
            subscription_key, token_provider and token_provider(), x_ms_useragent
        )

    def begin_analyze(self):
        """
        Initiates an analysis request using either a local file or a URL.

        Determines the content type based on the file location and sends a POST request
        to the Content Understanding service.

        Returns:
            Response: The HTTP response from the service.

        Raises:
            ValueError: If the file location is invalid.
            HTTPError: If the request fails.
        """
        if Path(self.file_location).exists():
            with open(self.file_location, "rb") as file:
                data = file.read()
            headers = {"Content-Type": "application/octet-stream"}
        elif "https://" in self.file_location or "http://" in self.file_location:
            data = {"url": self.file_location}
            headers = {"Content-Type": "application/json"}
        else:
            raise ValueError("File location must be a valid path or URL.")

        headers.update(self._headers)
        if isinstance(data, dict):
            response = requests.post(
                url=self._get_analyze_url(
                    self.endpoint, self.api_version, self.analyzer_id
                ),
                headers=headers,
                json=data,
            )
        else:
            response = requests.post(
                url=self._get_analyze_url(
                    self.endpoint, self.api_version, self.analyzer_id
                ),
                headers=headers,
                data=data,
            )

        response.raise_for_status()
        self._logger.info(
            f"Analyzing file {self.file_location} with analyzer: {self.analyzer_id}"
        )
        return response

    def poll_result(
        self,
        response: requests.Response,
        timeout_seconds: int = 120,
        polling_interval_seconds: int = 2,
    ) -> dict[str, Any]:
        """
        Polls the operation result until it completes or times out.

        Continuously checks the status of the asynchronous operation using the
        operation-location header from the initial response.

        Args:
            response (Response): Initial response containing operation-location.
            timeout_seconds (int): Max time to wait for completion.
            polling_interval_seconds (int): Time between polling attempts.

        Returns:
            dict: Final result of the operation.

        Raises:
            ValueError: If operation-location is missing.
            TimeoutError: If operation exceeds timeout.
            RuntimeError: If operation fails.
        """
        operation_location = response.headers.get("operation-location", "")
        if not operation_location:
            raise ValueError("Operation location not found in response headers.")

        headers = {"Content-Type": "application/json"}
        headers.update(self._headers)

        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            self._logger.info(
                "Waiting for service response", extra={"elapsed": elapsed_time}
            )
            if elapsed_time > timeout_seconds:
                raise TimeoutError(
                    f"Operation timed out after {timeout_seconds:.2f} seconds."
                )

            response = requests.get(operation_location, headers=self._headers)
            response.raise_for_status()
            result = cast(dict[str, str], response.json())
            status = result.get("status", "").lower()
            if status == "succeeded":
                self._logger.info(
                    f"Request result is ready after {elapsed_time:.2f} seconds."
                )
                return response.json()
            elif status == "failed":
                self._logger.error(f"Request failed. Reason: {response.json()}")
                raise RuntimeError("Request failed.")
            else:
                self._logger.info(
                    f"Request {operation_location.split('/')[-1].split('?')[0]} in progress ..."
                )
            time.sleep(polling_interval_seconds)

    def _get_analyze_url(self, endpoint: str, api_version: str, analyzer_id: str):
        """
        Constructs the full URL for the analyze request.

        Args:
            endpoint (str): Base endpoint of the service.
            api_version (str): API version to use.
            analyzer_id (str): Analyzer ID.

        Returns:
            str: Fully constructed URL for the analyze request.
        """
        return f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze?api-version={api_version}&stringEncoding=utf16"

    def _get_headers(
        self, subscription_key: str | None, api_token: str | None, x_ms_useragent: str
    ) -> dict[str, str]:
        """
        Builds the headers required for the HTTP requests.

        Args:
            subscription_key (str, optional): Subscription key for authentication.
            api_token (str, optional): AAD token for authentication.
            x_ms_useragent (str): Custom user agent string.

        Returns:
            dict: Dictionary of HTTP headers.
        """
        headers = (
            {"Ocp-Apim-Subscription-Key": subscription_key}
            if subscription_key
            else {"Authorization": f"Bearer {api_token}"}
        )
        headers["x-ms-useragent"] = x_ms_useragent
        return headers
