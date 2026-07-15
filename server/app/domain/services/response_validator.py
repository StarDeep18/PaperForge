"""
Response Validator.

Validates the content, size, and formatting of generated LLM outputs.
"""

from typing import Optional
from app.domain.exceptions import EmptyGeneration, ResponseValidationFailed


class ResponseValidator:
    """
    Validates LLM-generated text against structural and safety requirements.
    """

    def __init__(self, max_length: int = 100000):
        self._max_length = max_length

    def validate(
        self,
        text: Optional[str],
        provider: str,
        model: str,
        required_fields: list[str] | None = None,
    ) -> list[str]:
        """
        Validate generated response.

        Args:
            text: Raw response string from the provider.
            provider: Name of the LLM provider.
            model: Name of the LLM model.
            required_fields: Optional list of fields/substrings that must exist in the text.

        Returns:
            A list of warning strings.

        Raises:
            EmptyGeneration: If the response is null or only whitespace.
            ResponseValidationFailed: If the response violates size, safety, or formatting constraints.
        """
        warnings = []

        # ── 1. Empty Check ───────────────────────────────────────────
        if not text or not text.strip():
            raise EmptyGeneration(provider, model)

        # ── 2. Size Check ────────────────────────────────────────────
        if len(text) > self._max_length:
            raise ResponseValidationFailed(
                f"Generated response size ({len(text)} characters) "
                f"exceeds the configured maximum limit of {self._max_length}."
            )

        # ── 3. Unsafe / Malformed Formatting ──────────────────────────
        # Check for unclosed markdown formatting code blocks
        if text.count("```") % 2 != 0:
            warnings.append("Unclosed markdown code block ('```') detected in output.")

        # Check for unclosed square brackets (could indicate cut off citations)
        if text.count("[") != text.count("]"):
            warnings.append("Mismatched brackets detected in output; possible truncated content.")

        # ── 4. Missing Required Fields ───────────────────────────────
        if required_fields:
            for field in required_fields:
                if field not in text:
                    raise ResponseValidationFailed(
                        f"Validation failed: Response is missing required term/field '{field}'."
                    )

        # ── 5. Future Hallucination Detection Placeholder ──────────────
        # Currently raises warnings for typical AI refusal boilerplates
        lower_text = text.lower()
        if "as an ai" in lower_text or "i do not have access" in lower_text:
            warnings.append("Response contains typical AI model refusal boilerplate.")

        return warnings
