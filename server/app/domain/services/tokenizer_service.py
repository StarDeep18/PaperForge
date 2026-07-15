"""
Tokenizer Service Interface.

Defines the contract for estimating token counts, allowing easy transition
from simple character heuristics to official model tokenizers.
"""

import math
from abc import ABC, abstractmethod


class TokenizerService(ABC):
    """
    Abstract interface for model tokenizers.
    """

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count of the given text fragment.
        """
        pass


class CharacterLengthTokenizerService(TokenizerService):
    """
    Default simple character heuristic tokenizer.
    Typically assumes ~4 characters per token.
    """

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return math.ceil(len(text) / 4)
