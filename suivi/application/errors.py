class StorageError(Exception):
    """Un adaptateur de stockage n'a pas pu lire ou écrire (fichier verrouillé, base inaccessible...)."""

    def __init__(self, message: str, locked: bool = False):
        super().__init__(message)
        self.locked = locked   # True : la ressource est occupée par un autre programme (ex. Excel)
