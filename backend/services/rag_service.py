import re
from services.embedding_service import EmbeddingService
from services.llm_service import LLMService
from services.vector_store import VectorStore
from services.guardrails import quick_topic_check, build_off_topic_response
from prompts.system_prompt import SYSTEM_PROMPT, TOPIC_CHECK_PROMPT


class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        self.vector_store = VectorStore()

    async def process_query(self, message: str,
                            conversation_history: list,
                            page_url: str = None) -> dict:
        # Step 1: Guardrails - topic check
        topic = quick_topic_check(message)
        if topic == "LIKELY_OFF_TOPIC":
            return build_off_topic_response()
        if topic == "UNCERTAIN":
            classification = self.llm_service.classify(
                TOPIC_CHECK_PROMPT.format(message=message)
            )
            if "OFF_TOPIC" in classification.upper():
                return build_off_topic_response()

        # Step 2: Detect intent and extract entities
        intent = self._detect_intent(message)
        entities = self._extract_entities(message)

        # Extract PS number from the currently viewed page URL
        if page_url:
            page_ps = re.search(r'PS(\d{5,})', page_url)
            if page_ps:
                page_ps_number = f"PS{page_ps.group(1)}"
                if page_ps_number not in entities.get("ps_numbers", []):
                    entities.setdefault("ps_numbers", []).insert(
                        0, page_ps_number
                    )

        # Step 3: Embed query and search vector store
        query_embedding = self.embedding_service.embed(message)

        # If a specific PS number is mentioned (or detected from page),
        # get ALL chunks for that part first
        results = None
        if entities.get("ps_numbers"):
            ps_num = entities["ps_numbers"][0]
            results = self.vector_store.search(
                query_embedding, n_results=5,
                where={"ps_number": ps_num}
            )

        # If no PS number or no results, use intent-based filtering
        if (not results or not results.get("documents")
                or not results["documents"][0]):
            where_filter = None
            if intent == "COMPATIBILITY_CHECK":
                where_filter = {"chunk_type": "compatibility"}
            elif intent == "TROUBLESHOOT":
                where_filter = {"chunk_type": "troubleshooting"}

            results = self.vector_store.search(
                query_embedding, n_results=5, where=where_filter
            )

        # Final fallback: unfiltered semantic search
        if (not results or not results.get("documents")
                or not results["documents"][0]):
            results = self.vector_store.search(query_embedding, n_results=5)

        # Step 4: Build context from retrieved documents
        context = self._build_context(results)

        # Step 5: Generate response with GPT-4
        system_prompt = SYSTEM_PROMPT.format(context=context)
        messages = conversation_history[-10:] + [
            {"role": "user", "content": message}
        ]
        response_text = self.llm_service.chat(system_prompt, messages)

        # Step 6: Extract part cards from search results
        part_cards = self._extract_part_cards(results)

        # Step 7: Generate suggested follow-up queries
        suggested = self._generate_suggestions(intent, entities)

        return {
            "role": "assistant",
            "content": response_text,
            "parts": part_cards,
            "suggested_queries": suggested
        }

    def _detect_intent(self, message: str) -> str:
        lower = message.lower()
        if any(w in lower for w in [
            "compatible", "fit", "work with", "right part for",
            "does it fit", "will it work"
        ]):
            return "COMPATIBILITY_CHECK"
        if any(w in lower for w in [
            "install", "replace", "how to put", "instructions",
            "step by step", "installation"
        ]):
            return "INSTALLATION_HELP"
        if any(w in lower for w in [
            "not working", "broken", "fix", "problem", "noise",
            "leak", "won't", "doesn't", "troubleshoot", "repair"
        ]):
            return "TROUBLESHOOT"
        if re.search(r'PS\d+', message, re.IGNORECASE):
            return "PART_LOOKUP"
        return "GENERAL"

    def _extract_entities(self, message: str) -> dict:
        ps_numbers = re.findall(r'PS\d{6,}', message, re.IGNORECASE)
        model_numbers = re.findall(
            r'\b[A-Z]{2,}\d{3,}[A-Z]*\d*[A-Z]*\b', message
        )
        return {
            "ps_numbers": [p.upper() for p in ps_numbers],
            "model_numbers": model_numbers
        }

    def _build_context(self, results: dict) -> str:
        if (not results or not results.get("documents")
                or not results["documents"][0]):
            return "No relevant information found in the database."

        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results.get("metadatas") else {}
            chunk_type = meta.get("chunk_type", "general")
            source = meta.get("source_url", "")
            header = f"[Source {i+1} - {chunk_type}]"
            if source:
                header += f" ({source})"
            chunks.append(f"{header}\n{doc}")
        return "\n\n---\n\n".join(chunks)

    def _extract_part_cards(self, results: dict) -> list:
        if (not results or not results.get("metadatas")
                or not results["metadatas"][0]):
            return []

        seen = set()
        cards = []
        for meta in results["metadatas"][0]:
            ps = meta.get("ps_number")
            if ps and ps not in seen:
                seen.add(ps)
                cards.append({
                    "ps_number": ps,
                    "name": meta.get("name", ""),
                    "price": meta.get("price"),
                    "image_url": meta.get("image_url"),
                    "part_url": meta.get("source_url"),
                    "oem_part_number": meta.get("oem_part_number")
                })
        return cards[:3]

    def _generate_suggestions(self, intent: str, entities: dict) -> list:
        if intent == "PART_LOOKUP" and entities.get("ps_numbers"):
            ps = entities["ps_numbers"][0]
            return [
                f"What models is {ps} compatible with?",
                f"How do I install {ps}?",
                "Show me similar parts"
            ]
        elif intent == "TROUBLESHOOT":
            return [
                "What part do I need to fix this?",
                "Show me installation instructions",
                "Find compatible parts for my model"
            ]
        elif intent == "COMPATIBILITY_CHECK":
            return [
                "Show me installation instructions",
                "What does this part do?",
                "Are there alternatives?"
            ]
        elif intent == "INSTALLATION_HELP":
            return [
                "What tools do I need?",
                "Is there a video guide?",
                "Check part compatibility"
            ]
        return [
            "Help me find a refrigerator part",
            "My dishwasher is not draining",
            "Check part compatibility"
        ]
