"""
NEXUS Grounded RAG Generation Engine
Coordinates semantic retrieval, evidence grounding, strict provenance prompting,
abstention enforcement, citation tracking, and conversation persistence.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Generator
from pathlib import Path

from backend.generation.ollama_client import BaseLLMClient, OllamaClient, MockLLMClient, LLMError
from backend.retrieval.retriever import SemanticRetriever, get_default_retriever
from backend.services.conversation_service import add_message, get_conversation

logger = logging.getLogger("nexus.rag_engine")

# Strict provenance system prompt
NEXUS_SYSTEM_PROMPT = """You are NEXUS, an offline-first, domain-specific tactical knowledge intelligence assistant.
Your sole mission is to provide accurate, objective, evidence-backed answers strictly derived from the provided authorized reference passages.

OPERATIONAL DIRECTIVES:
1. STRICT PROVENANCE: Base your answer EXCLUSIVELY on the provided authorized passages. Never introduce external assumptions, speculative extrapolation, or unverified claims.
2. CITATION DISCIPLINE: For every fact or statement drawn from a reference, immediately cite it inline using the exact reference tag, e.g., [REF-1], [REF-2].
3. STRICT ABSTENTION: If the provided reference passages do not contain enough facts to answer the question completely and accurately, you MUST reply:
"The authorized repository does not contain sufficient verified information to answer this inquiry."
Do not attempt to guess or hallucinate.
4. TACTICAL BREVITY: Be concise, clear, and structured. Avoid conversational filler or apologies.
"""

ABSTENTION_MESSAGE = (
    "The authorized repository does not contain sufficient verified information to answer this inquiry. "
    "Please refine your query or consult an authorized administrator to ingest relevant documentation."
)


class RAGEngine:
    """
    Core Grounded Retrieval-Augmented Generation Engine.
    Enforces evidence sufficiency before generation, grounds prompt with citations,
    and resolves citations from generated text.
    """

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        retriever: Optional[SemanticRetriever] = None,
        default_top_k: int = 4,
        similarity_threshold: float = 0.35
    ):
        self.llm_client = llm_client or OllamaClient()
        self.retriever = retriever or get_default_retriever()
        self.default_top_k = default_top_k
        self.similarity_threshold = similarity_threshold

    def _build_grounded_prompt(
        self,
        query: str,
        citations: List[Dict[str, Any]]
    ) -> str:
        """
        Assemble grounded evidence block with indexed reference tags [REF-1], [REF-2].
        """
        evidence_lines = []
        evidence_lines.append("=== AUTHORIZED REFERENCE PASSAGES ===")
        for i, c in enumerate(citations, start=1):
            doc_name = c.get("filename", "Unknown Document")
            page = c.get("page_number", 1)
            domain = c.get("domain", "General")
            score = c.get("similarity_score", 0.0)
            text = c.get("content", "").strip()

            evidence_lines.append(
                f"[REF-{i}] Document: {doc_name} | Page: {page} | Domain: {domain} | Relevance: {score:.2f}\n"
                f"{text}\n"
            )

        evidence_lines.append("=== END OF AUTHORIZED PASSAGES ===")
        evidence_lines.append("")
        evidence_lines.append(f"USER INQUIRY: {query}")
        evidence_lines.append("")
        evidence_lines.append(
            "INSTRUCTIONS: Synthesize a factual, objective answer citing the applicable [REF-X] tags. "
            "If the references do not contain the answer, state that the repository has insufficient information."
        )

        return "\n".join(evidence_lines)

    def _extract_citations(
        self,
        answer_text: str,
        retrieved_citations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Inspect answer for cited tags ([REF-1], [REF-2]) and map them to full source metadata.
        """
        referenced_indices = set()
        matches = re.findall(r'\[REF-(\d+)\]', answer_text, flags=re.IGNORECASE)
        for m in matches:
            try:
                idx = int(m) - 1
                if 0 <= idx < len(retrieved_citations):
                    referenced_indices.add(idx)
            except ValueError:
                continue

        # If model explicitly cited tags, return those specifically
        if referenced_indices:
            used_citations = []
            for idx in sorted(referenced_indices):
                cited = dict(retrieved_citations[idx])
                cited["ref_tag"] = f"[REF-{idx + 1}]"
                used_citations.append(cited)
            return used_citations

        # Fallback: If answer is not an abstention, attach retrieved citations with tag
        if ABSTENTION_MESSAGE.lower() not in answer_text.lower():
            annotated = []
            for i, c in enumerate(retrieved_citations, start=1):
                item = dict(c)
                item["ref_tag"] = f"[REF-{i}]"
                annotated.append(item)
            return annotated

        return []

    def answer_query(
        self,
        query: str,
        user_id: int,
        username: str,
        domain: Optional[str] = None,
        conversation_id: Optional[str] = None,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        custom_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Execute full Grounded RAG flow:
        1. Query semantic retrieval.
        2. Verify evidence sufficiency / threshold.
        3. If insufficient, abstain immediately without wasting compute.
        4. If sufficient, construct grounded prompt and invoke local LLM.
        5. Map citations and persist message to SQLite conversation history.
        """
        cleaned_query = query.strip()
        if not cleaned_query:
            return {
                "answer": "Query cannot be empty. Please enter a valid inquiry.",
                "citations": [],
                "abstained": True,
                "confidence_score": 0.0,
                "evidence_count": 0
            }

        k = top_k or self.default_top_k
        thresh = threshold if threshold is not None else self.similarity_threshold

        # Step 1: Semantic Retrieval
        retrieval_res = self.retriever.retrieve_evidence(
            query=cleaned_query,
            user_id=user_id,
            username=username,
            domain=domain,
            top_k=k,
            threshold=thresh,
            custom_path=custom_path
        )

        citations = retrieval_res.get("citations", [])
        is_sufficient = retrieval_res.get("is_sufficient", False)

        # Step 2: Strict Abstention Check
        if not is_sufficient or not citations:
            answer = ABSTENTION_MESSAGE
            abstained = True
            active_citations = []

            # Save to conversation history if ID provided
            if conversation_id:
                try:
                    add_message(
                        conversation_id=conversation_id,
                        role="user",
                        content=cleaned_query,
                        user_id=user_id,
                        custom_path=custom_path
                    )
                    add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=answer,
                        citations=active_citations,
                        user_id=user_id,
                        custom_path=custom_path
                    )
                except Exception as exc:
                    logger.warning("Failed to persist conversation history: %s", exc)

            return {
                "answer": answer,
                "citations": active_citations,
                "abstained": abstained,
                "confidence_score": 0.0,
                "evidence_count": 0,
                "all_retrieved": []
            }

        # Step 3: Build Grounded Prompt
        grounded_prompt = self._build_grounded_prompt(cleaned_query, citations)

        # Step 4: Invoke Local LLM
        try:
            raw_answer = self.llm_client.generate(
                prompt=grounded_prompt,
                system_prompt=NEXUS_SYSTEM_PROMPT
            )
        except LLMError as exc:
            logger.error("LLM inference error: %s", exc)
            raw_answer = (
                f"LLM INFERENCE NOTICE: The local language model is currently unavailable or busy ({exc}). "
                "However, verified source evidence was successfully retrieved below."
            )

        # Step 5: Resolve Citations
        active_citations = self._extract_citations(raw_answer, citations)
        top_score = citations[0].get("similarity_score", 0.0) if citations else 0.0

        # Step 6: Persist in SQLite
        if conversation_id:
            try:
                add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=cleaned_query,
                    user_id=user_id,
                    custom_path=custom_path
                )
                add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=raw_answer,
                    citations=active_citations,
                    user_id=user_id,
                    custom_path=custom_path
                )
            except Exception as exc:
                logger.warning("Failed to persist conversation history: %s", exc)

        return {
            "answer": raw_answer,
            "citations": active_citations,
            "abstained": False,
            "confidence_score": float(top_score),
            "evidence_count": len(active_citations),
            "all_retrieved": citations
        }


def get_default_rag_engine() -> RAGEngine:
    """Return a default configured RAGEngine instance."""
    return RAGEngine()

