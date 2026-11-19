import re
import unicodedata


def slug(text: str) -> str:
    """'Épargne BNI' -> 'epargne_bni' (pour construire des noms de fichiers)."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_") or "portefeuille"
