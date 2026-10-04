class AmatistaEngineError(Exception):
    """Error base de Amatista Engine."""


class InvalidPracticeError(AmatistaEngineError):
    """La práctica declarativa no es válida.

    errors trae todos los problemas encontrados (el compilador no se detiene
    en el primero); el mensaje es el primero de ellos.
    """

    def __init__(self, message: str, errors=None):
        super().__init__(message)
        self.errors = list(errors) if errors else [message]
