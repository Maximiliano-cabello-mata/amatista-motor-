"""Excepciones del motor (AmatistaEngineError y sus derivadas)."""
class AmatistaEngineError(Exception):
    """Error base de Amatista Engine."""


class InvalidPracticeError(AmatistaEngineError):
    """La práctica declarativa no es válida.

    errors trae todos los problemas encontrados (el compilador no se detiene
    en el primero); el mensaje es el primero de ellos.
    """

    def __init__(self, message: str, errors=None):
        """Guarda el mensaje principal y la lista de errores concretos (para mostrarlos todos al autor de la práctica)."""
        super().__init__(message)
        self.errors = list(errors) if errors else [message]
