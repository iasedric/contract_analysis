from pathlib import Path
from azure.identity import DefaultAzureCredential
from contract_analysis import Translation
from contract_analysis import Document
from contract_analysis import DocumentIntelligence
from contract_analysis import OpenAIGPT
from contract_analysis import ContentUnderstanding, Settings
from typing import Optional, Dict, Union, Callable

PromptRegistry = Dict[str, Union[str, Callable[[], str]]]

class ContractAnalysis:
    def __init__(
        self,
        document_path: str,
        target_language: str,
        translator_endpoint: str,
        translator_region: str,
        cu_endpoint: str,
        cu_api_version: str,
        cu_subscription_key: str,
        cu_token_provider: str,
        cu_analyzer_id: str,
        di_endpoint: str,
        di_model_id: str,
        gpt_api_version: str,
        gpt_endpoint: str,
        gpt_token_scope: str = "https://cognitiveservices.azure.com/.default",
        di_fields_list: Optional[list] = None,
        prompt_registry: Optional[PromptRegistry] = None,
    ):
        self.document_path = Path(document_path)
        self.target_language = target_language

        self.translator_endpoint = translator_endpoint
        self.translator_region = translator_region

        self.di_endpoint = di_endpoint
        self.di_model_id = di_model_id
        self.di_fields_list = di_fields_list

        self.cu_endpoint = cu_endpoint
        self.cu_api_version = cu_api_version
        self.cu_subscription_key = cu_subscription_key
        self.cu_token_provider = cu_token_provider
        self.cu_analyzer_id = cu_analyzer_id

        self.translator_credential = DefaultAzureCredential()
        self.di_credential = DefaultAzureCredential()
        self.gpt_credential = DefaultAzureCredential()

        self.document = Document.from_file(self.document_path)
        self.document.ensure_pdf_exists()

        self.translator = Translation(
            credential=self.translator_credential,
            translator_endpoint=self.translator_endpoint,
            translator_region=self.translator_region,
            target_language=self.target_language,
            document=self.document
        )

        self.document_intelligence = DocumentIntelligence(
            credential=self.di_credential,
            di_endpoint=self.di_endpoint,
            di_model_id=self.di_model_id,
            document_pdf_path=str(self.document.pdf_path_to_use)
        )

        if self.di_fields_list:
            self.document_intelligence.init_field_dict(self.di_fields_list)

        settings = Settings(
            endpoint=self.cu_endpoint,
            api_version=self.cu_api_version,
            subscription_key=self.cu_subscription_key,
            aad_token="AZURE_CONTENT_UNDERSTANDING_AAD_TOKEN",
        )
        self.content_understanding = ContentUnderstanding(
            settings.endpoint,
            settings.api_version,
            subscription_key=settings.subscription_key,
            token_provider=settings.token_provider,
            analyzer_id=self.cu_analyzer_id,
        )

        self.gpt = OpenAIGPT(
            prompt_registry=prompt_registry or {},
            gpt_credential=self.gpt_credential,
            api_version=gpt_api_version,
            azure_endpoint=gpt_endpoint,
            token_scope=gpt_token_scope
        )

    def reset_gpt_credential(self, new_credential, api_version, azure_endpoint, token_scope="https://cognitiveservices.azure.com/.default"):
        self.gpt_credential = new_credential
        self.gpt = OpenAIGPT(
            prompt_registry=self.gpt.prompt_registry,
            gpt_credential=self.gpt_credential,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            token_scope=token_scope
        )

    @property
    def document_layout_pages(self):
        return self.document_intelligence.document_layout_pages

    @property
    def field_dict(self):
        return self.document_intelligence.field_dict

    @property
    def field_confidence_dict(self):
        return self.document_intelligence.field_confidence_dict
