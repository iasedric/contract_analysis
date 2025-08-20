from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from typing import List, Dict

class DocumentIntelligence:
    def __init__(self, credential: AzureKeyCredential, di_endpoint: str,
                 di_model_id: str, document_pdf_path: str):
        """
        Initializes the Document Intelligence client with credentials and configuration.
        """
        self.credential = credential
        self.di_endpoint = di_endpoint
        self.di_model_id = di_model_id
        self.document_pdf_path_to_use = document_pdf_path

        self.document_analysis_client: DocumentAnalysisClient = None
        self.document_layout_pages: List[str] = []
        self.field_dict: Dict[str, str] = {}
        self.field_confidence_dict: Dict[str, float] = {}

    def init_field_dict(self, fields_list: List[str]):
        """
        Initializes dictionaries for field values and confidence scores.
        """
        self.field_dict = {field: None for field in fields_list}
        self.field_confidence_dict = {field: 0.0 for field in fields_list}

    def init_document_analysis_client(self):
        """
        Initializes the Azure Document Analysis client.
        """
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=self.di_endpoint,
            credential=self.credential
        )

    def analyse_document_layout(self):
        """
        Analyzes the document layout using the prebuilt-layout model.
        Extracts and stores text per page.
        """
        with open(self.document_pdf_path_to_use, "rb") as f:
            document = f.read()

        poller = self.document_analysis_client.begin_analyze_document("prebuilt-layout", document)
        result = poller.result()

        self.document_layout_pages.clear()
        for page in result.pages:
            page_text = "\n".join([line.content for line in page.lines])
            self.document_layout_pages.append(page_text)

    def extract_document_fields(self):
        """
        Extracts structured fields using a custom model.
        Populates field values and confidence scores.
        """
        with open(self.document_pdf_path_to_use, "rb") as f:
            document = f.read()

        poller = self.document_analysis_client.begin_analyze_document(self.di_model_id, document)
        result = poller.result()

        for doc in result.documents:
            for name, field in doc.fields.items():
                value = field.value if field.value else field.content
                try:
                    self.field_dict[name] = value
                    self.field_confidence_dict[name] = field.confidence
                except Exception as e:
                    print(f"Error processing field '{name}': {e}")
