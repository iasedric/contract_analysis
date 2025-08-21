import requests
from enum import Enum
from azure.core.credentials import TokenCredential
from contract_analysis.document import Document

class TranslationAction(Enum):
    TRANSLATE = "translate"
    DETECT = "detect"

class Translation:
    def __init__(self, credential: TokenCredential, translator_endpoint: str, translator_region: str,
                 target_language: str, document: Document):
        self.credential = credential
        self.translator_endpoint = translator_endpoint
        self.translator_region = translator_region
        self.target_language = target_language
        self.document = document

    def _get_headers(self):
        token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
        return {
            "Ocp-Apim-Subscription-Region": self.translator_region,
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }

    def translate_text(self, text: str = None, action: TranslationAction = TranslationAction.TRANSLATE) -> str:
        if action == TranslationAction.DETECT:
            url = f"{self.translator_endpoint}/detect?api-version=3.0"
            body = [{"text": self.document.extract_text()}]
        else:
            url = f"{self.translator_endpoint}/translate?api-version=3.0&to={self.target_language}"
            body = [{"text": text}]

        response = requests.post(url, headers=self._get_headers(), json=body)
        if response.status_code != 200:
            raise Exception(f"Request failed. Reason: {response.json()}")

        result = response.json()
        if action == TranslationAction.DETECT:
            return result[0]["detectedLanguage"]["language"]
        else:
            return result[0]["translations"][0]["text"]

    def translate_document(self):
        translated_paragraphs = []
        for p in self.document.get_paragraphs():
            text = p.strip()
            translated_text = self.translate_text(text)
            translated_paragraphs.append(translated_text)
        self.document.save_translated(translated_paragraphs)
        self.document.set_paths_to_use(translated=True)

    def check_language_and_translate_if_needed(self):
        detected_language = self.translate_text(action=TranslationAction.DETECT)
        if detected_language != self.target_language:
            self.translate_document()
        else:
            self.document.set_paths_to_use(translated=False)
