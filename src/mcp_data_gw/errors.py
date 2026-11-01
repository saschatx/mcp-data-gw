"""Controlled errors shared by the application layers."""


class GatewayError(Exception):
    """A safe, client-visible domain error."""

    def __init__(self, code: str, message: str) -> None:
        """Format an error without exposing technical details or secrets.

        Args:
            code (str): Stable domain error identifier, such as INVALID_FILTER.
            message (str): Safe human-readable explanation suitable for clients.
        """
        self.code = code
        super().__init__(f"[{code}] {message}")
