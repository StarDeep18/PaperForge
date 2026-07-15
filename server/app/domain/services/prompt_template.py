"""
Prompt Templates.

Defines the interchangeable prompt templates for various PaperForge AI capabilities,
following the abstraction design requested in the architecture review.
"""

from abc import ABC, abstractmethod


class PromptTemplate(ABC):
    """
    Abstract interface for AI prompt templates.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the template."""
        pass

    @property
    @abstractmethod
    def system_instruction(self) -> str:
        """System instructions or prompt context."""
        pass

    @abstractmethod
    def format_user_prompt(
        self,
        query: str,
        context: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Format the user prompt with the query, history, and retrieved context."""
        pass


class DefaultRAGPromptTemplate(PromptTemplate):
    """
    Standard template for Retrieval-Augmented Generation answering.
    """

    @property
    def name(self) -> str:
        return "default_rag"

    @property
    def system_instruction(self) -> str:
        return (
            "You are PaperForge, an advanced scientific literature review AI assistant.\n"
            "Your goal is to answer the user's queries accurately, objectively, and comprehensively "
            "using ONLY the provided document context below.\n"
            "Adhere to the following constraints:\n"
            "1. Base your answer strictly on the provided context chunks. Do not assume or extrapolate beyond it.\n"
            "2. If the context is insufficient or does not contain the answer, state clearly that you cannot answer based on the provided documents.\n"
            "3. Keep the tone academic, precise, and professional."
        )

    def format_user_prompt(
        self,
        query: str,
        context: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        parts = []
        if context:
            parts.append(f"Context from retrieved literature:\n{context}")
        else:
            parts.append("No context from retrieved literature is available.")
        parts.append(f"User Query: {query}")
        return "\n\n".join(parts)


class SummarizationPromptTemplate(PromptTemplate):
    """
    Template for summarizing research papers/contexts.
    """

    @property
    def name(self) -> str:
        return "summarization"

    @property
    def system_instruction(self) -> str:
        return (
            "You are PaperForge, an expert in scientific summarization.\n"
            "Create a concise, structured, and informative summary of the provided text/documents.\n"
            "Highlight core contributions, methodology, and key findings."
        )

    def format_user_prompt(
        self,
        query: str,
        context: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        parts = [f"Text to summarize:\n{context}"]
        if query:
            parts.append(f"Focus instructions: {query}")
        return "\n\n".join(parts)


class LiteratureReviewPromptTemplate(PromptTemplate):
    """
    Template for generating literature reviews.
    """

    @property
    def name(self) -> str:
        return "literature_review"

    @property
    def system_instruction(self) -> str:
        return (
            "You are PaperForge, an expert academic writer.\n"
            "Perform a literature review based on the provided context.\n"
            "Synthesize different viewpoints, find connections between papers, and structure the analysis logically."
        )

    def format_user_prompt(
        self,
        query: str,
        context: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        parts = [f"Literature Context:\n{context}"]
        if query:
            parts.append(f"Review Topic/Query: {query}")
        return "\n\n".join(parts)


class PaperComparisonPromptTemplate(PromptTemplate):
    """
    Template for comparing multiple papers.
    """

    @property
    def name(self) -> str:
        return "paper_comparison"

    @property
    def system_instruction(self) -> str:
        return (
            "You are PaperForge, a researcher specializing in comparative analysis.\n"
            "Compare and contrast the papers and methods described in the context below.\n"
            "Construct a comparative analysis covering objectives, techniques, performance, and limitations."
        )

    def format_user_prompt(
        self,
        query: str,
        context: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        parts = [f"Retrieved Papers Context:\n{context}"]
        if query:
            parts.append(f"Comparison focus: {query}")
        return "\n\n".join(parts)


class ResearchGapPromptTemplate(PromptTemplate):
    """
    Template for identifying research gaps.
    """

    @property
    def name(self) -> str:
        return "research_gap"

    @property
    def system_instruction(self) -> str:
        return (
            "You are PaperForge, an academic research advisor.\n"
            "Analyze the provided literature context to identify unresolved problems, limitations, or research gaps.\n"
            "Suggest directions for future work."
        )

    def format_user_prompt(
        self,
        query: str,
        context: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        parts = [f"Literature Context:\n{context}"]
        if query:
            parts.append(f"Specific domain/query: {query}")
        return "\n\n".join(parts)


class FlashcardsPromptTemplate(PromptTemplate):
    """
    Template for flashcard generation.
    """

    @property
    def name(self) -> str:
        return "flashcards"

    @property
    def system_instruction(self) -> str:
        return (
            "You are PaperForge, an educational AI generator.\n"
            "Generate Q&A flashcards based on the key concepts in the provided text.\n"
            "Output each flashcard with a clear Question and a brief Answer."
        )

    def format_user_prompt(
        self,
        query: str,
        context: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        parts = [f"Source Text:\n{context}"]
        if query:
            parts.append(f"Generation instructions: {query}")
        return "\n\n".join(parts)


class QuizPromptTemplate(PromptTemplate):
    """
    Template for quiz generation.
    """

    @property
    def name(self) -> str:
        return "quiz"

    @property
    def system_instruction(self) -> str:
        return (
            "You are PaperForge, an academic assessor.\n"
            "Create a multiple-choice quiz based on the key facts in the provided text.\n"
            "For each question, provide 4 options (A, B, C, D) and specify the correct answer."
        )

    def format_user_prompt(
        self,
        query: str,
        context: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        parts = [f"Source Text:\n{context}"]
        if query:
            parts.append(f"Quiz topic/options: {query}")
        return "\n\n".join(parts)
