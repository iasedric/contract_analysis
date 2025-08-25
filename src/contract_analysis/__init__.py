"""
contract_analysis package

This package provides a modular framework for analyzing, translating, and understanding contract documents.
It integrates Azure AI services, OpenAI GPT, and custom logic for document processing.

Modules:
- document: Handles DOCX/PDF conversion and text extraction.
- translation: Translates documents using Azure Translator.
- document_intelligence: Extracts structured data using Azure Document Intelligence.
- content_understanding: Interfaces with Azure Content Understanding for semantic analysis.
- openai_gpt: Wraps Azure OpenAI GPT for prompt-based processing.
- contract_analysis: Orchestrates the full contract analysis pipeline.

Exports:
- Document
- Translation
- DocumentIntelligence
- ContentUnderstanding
- OpenAIGPT
- ContractAnalysis
"""


__version__ = "0.1.2"


from .document import Document
from .translation import Translation
from .document_intelligence import DocumentIntelligence
from .content_understanding import ContentUnderstanding
from .content_understanding import Settings
from .openai_gpt import OpenAIGPT
from .contract_analysis import ContractAnalysis

__all__ = [
    "Document",
    "Translation",
    "DocumentIntelligence",
    "ContentUnderstanding",
    "Settings",
    "OpenAIGPT",
    "ContractAnalysis",
]
