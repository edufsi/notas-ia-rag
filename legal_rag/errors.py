class LegalRAGError(RuntimeError):
    """Erro operacional esperado do serviço de recuperação."""


class IndexUnavailableError(LegalRAGError):
    """O índice solicitado não está disponível ou está desatualizado."""


class InvalidSearchError(LegalRAGError):
    """A consulta ou seus limites são inválidos."""

