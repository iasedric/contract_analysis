# contract_analysis.py

from pathlib import Path
from typing import Optional, Dict, Union, Callable, List

from azure.identity import DefaultAzureCredential

# Prefer relative imports inside the package to avoid circular import issues.
from .document import Document
from .translation import Translation
from .document_intelligence import DocumentIntelligence
from .openai_gpt import OpenAIGPT
from .content_understanding import ContentUnderstanding, Settings

PromptRegistry = Dict[str, Union[str, Callable[[], str]]]


class ContractAnalysis:
    """
    Orchestrator for contract processing where 'Document' and 'Translation' are mandatory,
    and 'OpenAI GPT', 'Document Intelligence (DI)', and 'Content Understanding (CU)' are optional.

    Supported usage patterns:
      - Translation + GPT
      - Translation + DI
      - Translation + CU
      - Translation only
      - Translation + any combination of (GPT, DI, CU)

    Notes:
      - PDF conversion is performed *only* if DI is configured (DI needs a PDF).
      - Properties that surface DI outputs will raise if DI is not configured.
    """

    def __init__(
        self,
        # --- Mandatory: Document + Translation ---
        document_path: str,
        target_language: str,
        translator_endpoint: str,
        translator_region: str,

        # --- Optional: OpenAI GPT ---
        gpt_api_version: Optional[str] = None,
        gpt_endpoint: Optional[str] = None,
        gpt_model: Optional[str] = None,  # Azure OpenAI deployment name
        gpt_token_scope: str = "https://cognitiveservices.azure.com/.default",
        prompt_registry: Optional[PromptRegistry] = None,

        # --- Optional: Document Intelligence ---
        di_endpoint: Optional[str] = None,
        di_model_id: Optional[str] = None,
        di_fields_list: Optional[List[str]] = None,

        # --- Optional: Content Understanding ---
        cu_endpoint: Optional[str] = None,
        cu_api_version: Optional[str] = None,
        cu_subscription_key: Optional[str] = None,
        cu_token_provider: Optional[str] = None,  # If provided, treated as an AAD token string
        cu_analyzer_id: Optional[str] = None,
    ):
        # --- Core: Document (always) ---
        self.document_path = Path(document_path)
        self.document = Document.from_file(self.document_path)

        # --- Core: Translation (always) ---
        self.translator_credential = DefaultAzureCredential()
        self.translator = Translation(
            credential=self.translator_credential,
            translator_endpoint=translator_endpoint,
            translator_region=translator_region,
            target_language=target_language,
            document=self.document,
        )

        # --- Optional: OpenAI GPT ---
        # Enforce all-or-nothing for GPT configuration to avoid constructing a client with a missing model.
        if any([gpt_api_version, gpt_endpoint, gpt_model]) and not all([gpt_api_version, gpt_endpoint, gpt_model]):
            raise ValueError(
                "If configuring GPT, you must provide gpt_api_version, gpt_endpoint, and gpt_model."
            )

        self.gpt: Optional[OpenAIGPT] = None
        self.gpt_credential: Optional[DefaultAzureCredential] = None
        if all([gpt_api_version, gpt_endpoint, gpt_model]):
            self.gpt_credential = DefaultAzureCredential()
            self.gpt = OpenAIGPT(
                prompt_registry=prompt_registry or {},
                gpt_credential=self.gpt_credential,
                api_version=gpt_api_version,      # type: ignore[arg-type]
                azure_endpoint=gpt_endpoint,      # type: ignore[arg-type]
                model=gpt_model,                  # type: ignore[arg-type]
                token_scope=gpt_token_scope,
            )

        # --- Optional: Document Intelligence (requires a PDF) ---
        self.document_intelligence: Optional[DocumentIntelligence] = None
        self.di_credential: Optional[DefaultAzureCredential] = None
        if di_endpoint and di_model_id:
            # Only DI needs a guaranteed PDF; perform conversion on demand.
            self.document.ensure_pdf_exists()
            self.di_credential = DefaultAzureCredential()
            pdf_path_to_use = str(self.document.pdf_path_to_use or self.document.original_pdf_path)
            self.document_intelligence = DocumentIntelligence(
                credential=self.di_credential,
                di_endpoint=di_endpoint,
                di_model_id=di_model_id,
                document_pdf_path=pdf_path_to_use,
            )
            if di_fields_list:
                self.document_intelligence.init_field_dict(di_fields_list)

        # --- Optional: Content Understanding ---
        self.content_understanding: Optional[ContentUnderstanding] = None
        if cu_endpoint and cu_api_version and (cu_subscription_key or cu_token_provider):
            # Use Settings to produce either subscription-key headers or AAD bearer token.
            settings = Settings(
                endpoint=cu_endpoint,
                api_version=cu_api_version,
                subscription_key=cu_subscription_key,
                aad_token=cu_token_provider,  # If provided, this becomes a token provider via Settings
            )
            self.content_understanding = ContentUnderstanding(
                settings.endpoint,
                settings.api_version,
                subscription_key=settings.subscription_key,
                token_provider=settings.token_provider,
                analyzer_id=cu_analyzer_id,
            )

    # ------------- Utilities -------------

    def reset_gpt_credential(
        self,
        new_credential,
        api_version: str,
        azure_endpoint: str,
        *,
        model: str,
        token_scope: str = "https://cognitiveservices.azure.com/.default",
    ):
        """
        (Re)build the GPT client with a new credential or endpoint.
        If GPT was not configured before, this enables it now.
        The 'model' argument is the Azure OpenAI *deployment name*.
        """
        self.gpt_credential = new_credential
        self.gpt = OpenAIGPT(
            prompt_registry=(self.gpt.prompt_registry if self.gpt else {}),
            gpt_credential=self.gpt_credential,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            model=model,
            token_scope=token_scope,
        )

    # ------------- DI-dependent properties -------------

    @property
    def document_layout_pages(self):
        if not self.document_intelligence:
            raise RuntimeError("DocumentIntelligence is not configured for this instance.")
        return self.document_intelligence.document_layout_pages

    @property
    def field_dict(self):
        if not self.document_intelligence:
            raise RuntimeError("DocumentIntelligence is not configured for this instance.")
        return self.document_intelligence.field_dict

    @property
    def field_confidence_dict(self):
        if not self.document_intelligence:
            raise RuntimeError("DocumentIntelligence is not configured for this instance.")
        return self.document_intelligence.field_confidence_dict
