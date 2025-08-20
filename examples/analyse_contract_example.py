import pathlib
import subprocess
from contract_analysis import ContractAnalysis

# Load configuration from a YAML file
import yaml

with open("configuration/config.yaml", "r") as f:
    config = yaml.safe_load(f)

target_language=config["translator"]["target_language"]
translator_endpoint=config["translator"]["endpoint"]
translator_region=config["translator"]["region"]
cu_endpoint=config["content_understanding"]["endpoint"]
cu_api_version=config["content_understanding"]["api_version"]
cu_subscription_key=config["content_understanding"]["subscription_key"]
cu_token_provider=config["content_understanding"]["token_provider"]
cu_analyzer_id=config["content_understanding"]["analyzer_id"]
di_endpoint=config["document_intelligence"]["endpoint"]
di_model_id=config["document_intelligence"]["model_id"]
gpt_api_version=config["openai_gpt"]["api_version"]
gpt_endpoint=config["openai_gpt"]["endpoint"]
gpt_model=config["openai_gpt"]["model"]



# def find_first_contract_file(contracts_dir: str = "contracts") -> pathlib.Path:
#     # Resolve path relative to the project root
#     base_path = pathlib.Path(__file__).resolve().parent.parent / contracts_dir
    

#     if not base_path.exists() or not base_path.is_dir():
#         raise FileNotFoundError(f"Contracts directory not found: {base_path}")

#     for file in base_path.iterdir():
#         if file.is_file() and file.suffix.lower() in [".pdf", ".docx"]:
#             return file.resolve()

#     raise FileNotFoundError(f"No .pdf or .docx files found in {base_path}")

def find_first_contract_file(contracts_dir: str = "contracts") -> pathlib.Path:
    base_path = pathlib.Path(__file__).resolve().parent / contracts_dir
    if not base_path.exists() or not base_path.is_dir():
        raise FileNotFoundError(f"Contracts directory not found: {base_path}")
    for file in base_path.iterdir():
        if file.is_file() and file.suffix.lower() in [".pdf", ".docx"]:
            return file.resolve()
    raise FileNotFoundError(f"No .pdf or .docx files found in {base_path}")




def remove_purview_protection(document_path: str):
    """
    Removes Microsoft Purview protection from a file using PowerShell.
    """
    powershell_command = [
        "powershell",
        "-Command",
        f'Remove-FileLabel -Path \"{document_path}\" -RemoveProtection'
    ]

    result = subprocess.run(powershell_command, capture_output=True, text=True)

    print({
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode
    })


def main():
    # Define the input file path in a Contracts directory (that should be in the same directory as this script with the contract files)
    file_path = find_first_contract_file()

    # Remove protection from the original file
    remove_purview_protection(str(file_path))

    # Define the custom prompt registry for OpenAI GPT checks
    custom_prompts = {
        "Partner_Prime": lambda: """
        You are a specialized contract auditor. Please identify if the given contract is a partner prime deal...
        [FULL PROMPT TEXT HERE]
        """,
        "Scope": lambda: """
        You are a specialized contract auditor. Looking at the text above coming from a commercial contract...
        [FULL PROMPT TEXT HERE]
        """,
        "Timelines": lambda: """
        You are a specialized contract auditor. Looking at the text above coming from a commercial contract...
        [FULL PROMPT TEXT HERE]
        """
    }

    # Define DI fields to extract (these are the fields that will be extracted from the document on which the model was trained)
    di_fields_list = [
        "Footer","CustomerName", "MSAffiliateName", "Support Services and Fees", "SupportSFStartDate",
        "SupportSFEndDate", "MasterAgreementType", "MasterAgreementReference",
        "MasterAgreementDate", "CustomerSignature", "MSAffiliateSignature",
        "Consulting Services and Fees.", "ConsultingSFStartDate", "ConsultingSFEndDate",
        "ConsultingSFTermination_TM", "ConsultingSFTermination_FixedFee",
        "Consulting Services and Fees Time and Material (Beratungsleistungen)",
        "ConsultingSFStartDate(Beratungsleistungen)", "ConsultingSFEndDate(Beratungsleistungen)",
        "ConsultingSFTermination(Beratungsleistungen)",
        "Consulting Services and Fees: Work Performances (Werkleistungen)",
        "ConsultingSFStartDate(Werkleistungen)", "ConsultingSFEndDate(Werkleistungen)",
        "ConsultingSFTermination(Werkleistungen)", "Total Services and Fees Summary.",
        "Limitation of Liability.", "Attachments.", "SupportSFSubtotal", "ConsultingSFSubtotal",
        "SupportSFFlexAllowance", "ConsultingSFFlexAllowance", "SupportSFReinbursableExpenses",
        "ConsultingSFReinbursableExpenses", "SupportSFBillingSchedule",
        "ConsultingSFBillingSchedule", "ConsultingSF(Werkleistungen)BillingSchedule"
    ]



    # Initialize ContractAnalysis
    
    contract_analysis = ContractAnalysis(
        document_path=str(file_path),
        target_language=target_language,
        translator_endpoint=translator_endpoint,
        translator_region=translator_region,
        cu_endpoint=cu_endpoint,
        cu_api_version=cu_api_version,
        cu_subscription_key=cu_subscription_key,
        cu_token_provider=cu_token_provider,
        cu_analyzer_id=cu_analyzer_id,
        di_endpoint=di_endpoint,
        di_model_id=di_model_id,
        gpt_api_version=gpt_api_version,
        gpt_endpoint=gpt_endpoint,
        gpt_model=gpt_model,
        gpt_token_scope="https://cognitiveservices.azure.com/.default",
        di_fields_list=di_fields_list,
        prompt_registry=custom_prompts
    )



    print("Checking language and translating if needed...")
    contract_analysis.translator.check_language_and_translate_if_needed()

    # Update PDF path after translation
    contract_analysis.document_intelligence.document_pdf_path_to_use = str(contract_analysis.document.pdf_path_to_use)

    # Remove protection from the final PDF (translated or original)
    remove_purview_protection(str(contract_analysis.document.pdf_path_to_use))


    print("Analyzing document layout...")
    contract_analysis.document_intelligence.init_document_analysis_client()
    contract_analysis.document_intelligence.analyse_document_layout()

    print("Extracting document fields...")
    contract_analysis.document_intelligence.extract_document_fields()

    print("Contract analysis completed.")

    # Print results
    print("\n📄 Document Layout (per page):")
    for i, page in enumerate(contract_analysis.document_layout_pages, 1):
        print(f"\n--- Page {i} ---\n{page}")

    print("\n📌 Extracted Fields:")
    for field, value in contract_analysis.field_dict.items():
        confidence = contract_analysis.field_confidence_dict.get(field, 0.0)
        print(f"{field}: {value} (Confidence: {confidence:.2f})")



    # Run content understanding with the provided schema
    contract_analysis.content_understanding.file_location = str(contract_analysis.document.pdf_path_to_use)
    contract_analysis.content_understanding.begin_analyze()

    # Run GPT checks
    full_text = "\n".join(contract_analysis.document_layout_pages)

    print("\n🤝 Partner Prime Check:")
    print(contract_analysis.gpt.run_prompt("Partner_Prime", full_text, clean=True)[0])

    print("\n📦 Scope Check:")
    print(contract_analysis.gpt.run_prompt("Scope", full_text, clean=True)[0])

    print("\n🗓️ Timelines Check:")
    print(contract_analysis.gpt.run_prompt("Timelines", full_text, clean=True)[0])


    print("\n✅ Contract analysis completed.")


if __name__ == "__main__":
    main()
