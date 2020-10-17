import unicodedata


class Parser:
    def normalize(self, text: str) -> str:
        if not text:
            return text
        return unicodedata.normalize('NFKC', text).replace('\n', '').strip()
