# Contract Analysis Library

A Python library for analyzing legal contracts using Azure services:

- Azure Document Intelligence  
- Azure Translator  
- Azure OpenAI  
- Azure Content Understanding  

## Features

- **Document Translation**: Automatically detect and translate contracts to a target language.  
- **Field Extraction**: Extract structured fields using Azure Document Intelligence from a pre-trained model.  
- **Layout Analysis**: Analyze document layout and extract text per page.  
- **Content Understanding**: Use Azure Content Understanding for semantic analysis (using pre-trained model).
- **GPT Integration**: Leverage Azure OpenAI GPT for advanced prompt-based analysis.  

## Installation

```bash
pip install contract-analysis
```

## Usage

```python

from contract_analysis import ContractAnalysis

analyzer = ContractAnalysis(
    document_path="<full-document-path>",
    target_language="<target-language>",  # e.g., 'en', 'fr'
    translator_endpoint="<your-translator-endpoint>",
    translator_region="<your-region>",  # e.g., 'eastus'

    # Optional: Content Understanding
    cu_endpoint="<your-cu-endpoint>",
    cu_api_version="<your-cu-api-version>",
    cu_subscription_key="<your-subscription-key>",
    cu_token_provider="<your-token-provider>",
    cu_analyzer_id="<your-analyzer-id>",

    # Optional: Document Intelligence
    di_endpoint="<your-di-endpoint>",
    di_model_id="<your-model-id>",
    di_fields_list=["PartyA", "PartyB", "EffectiveDate"],

    # Optional: GPT Integration
    gpt_api_version="<gpt-api-version>",
    gpt_endpoint="<gpt-endpoint>",
    gpt_model="<gpt-deployment-name>",
    prompt_registry={
        "PromptName1": lambda: """
        [FULL PROMPT TEXT HERE]
        """,
        "PromptName2": lambda: """
        [FULL PROMPT TEXT HERE]
        """
    }
)


```


## Running Tests
To run the test suite:

```bash
$env:PYTHONPATH="src"; python -m unittest discover -s tests -p "test_*.py"
```

## Project Structure


```bash
contract-analysis/
├── src/
│   └── contract_analysis/
│       ├── __init__.py
│       ├── document.py
│       ├── translation.py
│       ├── document_intelligence.py
│       ├── openai_gpt.py
│       ├── content_understanding.py
│       └── contract_analysis.py
├── tests/
│   ├── test_document.py
│   ├── test_translation.py
│   ├── test_document_intelligence.py
│   ├── test_openaigpt.py
│   ├── test_content_understanding.py
│   └── test_contract_analysis.py
├── examples/
│   ├── analyse_contract_example.py
│   └── compare_contracts_example.py
├── configuration/
│   └── config.yaml  # excluded from version control
├── contracts/
│   └── sample files  # excluded from version control
├── README.md
├── pyproject.toml
├── LICENSE
└── .gitignore
```


## License
MIT License

