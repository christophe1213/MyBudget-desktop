class DomainError(Exception):
    """Une règle métier n'est pas respectée (le message est destiné à l'utilisateur)."""


class AuthenticationError(DomainError):
    """Identifiants incorrects, compte verrouillé temporairement..."""
