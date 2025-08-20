# example_compare_two_contracts_gpt_only.py
"""
Compare two contracts using GPT only (no DI, no CU). Handles:
- .pdf or .docx inputs (PDF -> DOCX normalization via Document.from_file()).
- Purview-protected files (unprotected via PowerShell before processing).
- Large files via size-based chunking with overlap + per-chunk GPT comparison + final consolidation.
- No translation: comparison is performed in the original language for precision.

Requirements:
- Windows with Microsoft Word installed (Document uses Win32 COM).
- Valid Azure OpenAI endpoint and API version in configuration/config.yaml.
- Translator config is provided to ContractAnalysis (class requires it), but we DO NOT call translation here.
"""

import pathlib
import subprocess
from typing import List, Tuple

import yaml
from src.contract_analysis import ContractAnalysis

# =============================================================================
# Configuration
# =============================================================================
ROOT = pathlib.Path(__file__).parent
CONTRACTS_DIR = ROOT / "Contracts"

with open(ROOT / "configuration" / "config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

# Mandatory for the class (we won't invoke translation):
TARGET_LANG    = cfg["translator"]["target_language"]
TRANS_ENDPOINT = cfg["translator"]["endpoint"]
TRANS_REGION   = cfg["translator"]["region"]

# GPT settings (used here):
GPT_API_VERSION = cfg["openai_gpt"]["api_version"]
GPT_ENDPOINT    = cfg["openai_gpt"]["endpoint"]
GPT_MODEL       = cfg["openai_gpt"]["model"]


# =============================================================================
# File discovery & Purview unprotection
# =============================================================================
def find_two_contract_files() -> Tuple[str, str]:
    files = sorted(
        p for p in CONTRACTS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in [".pdf", ".docx"]
    )
    if len(files) < 2:
        raise FileNotFoundError(f"Need at least two .pdf/.docx files in {CONTRACTS_DIR}")
    return str(files[0].resolve()), str(files[1].resolve())


def remove_purview_protection(file_path: str):
    """
    Removes Microsoft Purview (AIP) protection:
        Remove-FileLabel -Path "<file>" -RemoveProtection
    Run BEFORE Word opens the file for conversion.
    """
    ps_cmd = [
        "powershell",
        "-Command",
        f'Remove-FileLabel -Path "{file_path}" -RemoveProtection'
    ]
    result = subprocess.run(ps_cmd, capture_output=True, text=True)
    print({
        "file": file_path,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode
    })


# =============================================================================
# Chunking utilities
# =============================================================================
def chunk_text(text: str, max_chars: int = 6000, overlap: int = 400) -> List[str]:
    """
    Size-based chunker with overlap to preserve context across boundaries.
    Keep chunks conservative because the GPT wrapper is configured with small max_tokens.
    """
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + max_chars)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def pair_chunks(a_chunks: List[str], b_chunks: List[str]) -> List[Tuple[int, str, str]]:
    """
    Pair chunks by index so we can compare chunk i of A vs chunk i of B.
    If one contract has more chunks, remaining pairs compare text vs "".
    """
    pairs: List[Tuple[int, str, str]] = []
    max_len = max(len(a_chunks), len(b_chunks))
    for i in range(max_len):
        a = a_chunks[i] if i < len(a_chunks) else ""
        b = b_chunks[i] if i < len(b_chunks) else ""
        pairs.append((i + 1, a, b))
    return pairs


# =============================================================================
# Prompts (merged: your instructions + structured outputs)
# =============================================================================
def chunk_prompt(chunk_index: int, total_chunks: int) -> str:
    """
    Per-chunk comparison prompt.
    Merges:
      - Your 1..4 instructions about material/high-risk changes and plain-English explanations.
      - Structured outputs (bullets, table-like text, JSON) for downstream processing.
    Scope is LIMITED to the content present in THIS CHUNK PAIR.
    """
    return f"""You are a contract analyst. Compare the content of CONTRACT A CHUNK {chunk_index}/{total_chunks}
            and CONTRACT B CHUNK {chunk_index}/{total_chunks} provided by the user in this message.

            Work ONLY with this chunk's content (do NOT assume context from other chunks).

            (Primary objectives for THIS CHUNK)
            1) Summarize the most material and high-risk changes (legal risk level > 70) between the two versions in this chunk,
            focusing on changes to contract terms, obligations, fees, support periods, data protection, and named contacts.
            2) For each such change, explain WHY it is material—specifically how it impacts legal, financial, operational,
            or compliance risk for the parties.
            3) Provide a plain-English summary of the visible content in this chunk: key terms, obligations, and high-risk
            areas (term, fees, support, data protection, named contacts) so a non-lawyer can understand the main points
            and risks present here.
            4) For each change identified as material or high-risk, explain in plain English why it is material—how it could
            affect the parties' rights, obligations, costs, compliance, or risk exposure.

            (Deliverables constrained to THIS CHUNK)
            A) Bullet list (concise) of material/high-risk (>70) differences.
            B) A table-like text:
            [Category | A | B | Delta | Risk/Impact | Severity (Low/Medium/High) | RiskScore(0-100)]
            C) JSON with all differences observed in this chunk (not only >70), with this schema:
            {{
            "chunk": {chunk_index},
            "differences": [
                {{
                "category": "",
                "contractA": "",
                "contractB": "",
                "delta": "",
                "riskImpact": "",
                "severity": "Low|Medium|High",
                "riskScore": 0
                }}
            ]
            }}

            Rules:
            - Compare in the original language; do NOT translate.
            - Quote short excerpts only as evidence when necessary.
            - If no material differences in this chunk, write "none" for A) and B), and return an empty array for C).
            - Do not speculate beyond this chunk's content.
            """


def consolidation_prompt() -> str:
    """
    Final consolidation prompt across all chunk outputs.
    Produces the global, deduplicated comparison and explanations per your instructions.
    """
    return """You are a contract analyst. Consolidate multiple CHUNK COMPARISONS into a single, deduplicated
            global comparison across CONTRACT A and CONTRACT B.

            INPUT: a list of chunk-level outputs (some may have "none"). Merge them coherently.

            (Primary objectives for the FULL CONTRACTS)
            1) Summarize the most material and high-risk changes (legal risk level > 70) between the two contract versions,
            focusing on changes to contract terms, obligations, fees, support periods, data protection, and named contacts.
            2) Explain WHY each such change is material—how it impacts legal, financial, operational, or compliance risk.
            3) Provide a plain-English summary of the overall contract: key terms, obligations, and high-risk areas (term, fees,
            support, data protection, named contacts) so a non-lawyer can understand the main points and risks.
            4) For each material or high-risk change identified, explain in plain English why it is material—specifically how it
            could affect the parties' rights, obligations, costs, compliance, or risk exposure.

            (Deliverables for the FULL CONSOLIDATION)
            A) Bullet list (concise) of material/high-risk (>70) differences across the entire contract.
            B) A single, deduplicated table-like text:
            [Category | A | B | Delta | Risk/Impact | Severity (Low/Medium/High) | RiskScore(0-100)]
            C) A single, deduplicated JSON:
            {
            "differences": [
                {"category":"","contractA":"","contractB":"","delta":"","riskImpact":"",
                "severity":"Low|Medium|High","riskScore":0}
            ]
            }

            Rules:
            - Keep the comparison in the original language.
            - Prefer precise wording based on chunk evidence; if items conflict, mark as "uncertain".
            - Avoid hallucinations; if information is missing, say so explicitly.
            """


# =============================================================================
# Pipeline helpers
# =============================================================================
def build_analysis_instance(path: str) -> ContractAnalysis:
    """
    Build a GPT-only ContractAnalysis instance.
    - Document + Translation are mandatory in the class, but we do NOT invoke translation here.
    - GPT is enabled; DI and CU are omitted.
    """
    return ContractAnalysis(
        document_path=path,
        target_language=TARGET_LANG,
        translator_endpoint=TRANS_ENDPOINT,
        translator_region=TRANS_REGION,
        gpt_api_version=GPT_API_VERSION,
        gpt_endpoint=GPT_ENDPOINT,
        gpt_model=GPT_MODEL,
        # No DI / CU
    )


def extract_text_for_gpt(ca: ContractAnalysis) -> str:
    """
    Extract raw text to feed GPT (original language). PDF->DOCX happens inside Document.from_file().
    """
    # Do NOT translate:
    # ca.translator.check_language_and_translate_if_needed()
    text = ca.document.extract_text() or ""
    return text


def compare_in_chunks(caA: ContractAnalysis, caB: ContractAnalysis,
                      max_chars: int = 6000, overlap: int = 400) -> str:
    """
    1) Split A and B into chunks.
    2) Compare pairwise chunk i of A vs i of B using GPT.
    3) Consolidate chunk-level outputs with a final GPT call.
    """
    textA = extract_text_for_gpt(caA)
    textB = extract_text_for_gpt(caB)

    a_chunks = chunk_text(textA, max_chars=max_chars, overlap=overlap)
    b_chunks = chunk_text(textB, max_chars=max_chars, overlap=overlap)
    pairs = pair_chunks(a_chunks, b_chunks)

    if not pairs:
        return "No text available to compare."

    per_chunk_outputs: List[str] = []
    total = len(pairs)

    print(f"Comparing in {total} chunk(s)...")
    for idx, a, b in pairs:
        prompt = chunk_prompt(idx, total)
        user_msg = f"### CONTRACT A CHUNK {idx}\n{a}\n\n### CONTRACT B CHUNK {idx}\n{b}"
        # clean=False => do not strip content; our chunking already controls size.
        result = caA.gpt.run(text=user_msg, prompt=prompt, clean=False)
        per_chunk_outputs.append(result[0])

    # Final consolidation
    joined = "\n\n--- CHUNK OUTPUT ---\n\n".join(per_chunk_outputs)
    final = caA.gpt.run(text=joined, prompt=consolidation_prompt(), clean=False)
    return final[0]


# =============================================================================
# Main
# =============================================================================
def main():
    # Find & unprotect files BEFORE Word tries to open them
    fA, fB = find_two_contract_files()
    remove_purview_protection(fA)
    remove_purview_protection(fB)

    # Build two GPT-only analysis instances (Translation present, not used)
    caA = build_analysis_instance(fA)
    caB = build_analysis_instance(fB)

    # Chunked comparison + consolidation
    final_report = compare_in_chunks(caA, caB, max_chars=6000, overlap=400)

    print("\n===== GPT Contract Comparison (GPT-only, chunked) =====\n")
    print(final_report)

    print("===== END OF REPORT =====")


if __name__ == "__main__":
    main()
