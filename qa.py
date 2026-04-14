"""
Transcript Q&A using a local or OpenAI-compatible LLM.

Hybrid routing:
- Transcripts < 25K tokens: full context sent directly to LLM
- Transcripts >= 25K tokens: RAG (sentence-transformers + ChromaDB)

Requires [qa] extra: uv sync --extra qa
"""

_TOKEN_THRESHOLD = 25_000
_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 50
_TOP_K = 5

_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer questions based only on the provided "
    "transcript context. If the answer is not in the context, say so."
)
_FULL_CONTEXT_TEMPLATE = "Transcript:\n{transcript}\n\nQuestion: {question}"
_RAG_TEMPLATE = "Relevant transcript excerpts:\n{chunks}\n\nQuestion: {question}"


def _estimate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def _chunk_text(text: str, size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    step = size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + size])
        if chunk:
            chunks.append(chunk)
        if i + size >= len(words):
            break
    return chunks


class TranscriptQA:
    def __init__(
        self,
        transcript_text: str,
        llm_url: str = "http://localhost:11434/v1",
        api_key: str | None = None,
        model: str = "llama3",
    ):
        self._transcript = transcript_text
        self._llm_url = llm_url
        self._api_key = api_key
        self._model = model
        self._use_rag = _estimate_tokens(transcript_text) >= _TOKEN_THRESHOLD
        self._rag_ready = False

    def ask(self, question: str) -> str:
        """Ask a question about the transcript. Returns the LLM's answer string."""
        try:
            from openai import OpenAI  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "Q&A requires the [qa] extra. Install with: uv sync --extra qa"
            ) from exc

        self._client = OpenAI(
            base_url=self._llm_url,
            api_key=self._api_key or "ollama",
        )

        if self._use_rag:
            if not self._rag_ready:
                self._setup_rag()
            return self._ask_rag(question)
        return self._ask_full_context(question)

    def _setup_rag(self) -> None:
        """Chunk, embed, and index the transcript. Called lazily on first ask if needed."""
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            import chromadb  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "Q&A RAG requires the [qa] extra. Install with: uv sync --extra qa"
            ) from exc

        chunks = _chunk_text(self._transcript)
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(chunks).tolist()

        client = chromadb.Client()
        # Delete existing collection if it exists (idempotent re-init)
        try:
            client.delete_collection("transcript")
        except Exception:
            pass
        collection = client.create_collection(
            name="transcript",
            metadata={"hnsw:space": "cosine"},
        )
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=[str(i) for i in range(len(chunks))],
        )
        self._rag_collection = collection
        self._rag_model = model
        self._rag_ready = True

    def _ask_full_context(self, question: str) -> str:
        """Full-context path: send entire transcript + question to LLM."""
        user_message = _FULL_CONTEXT_TEMPLATE.format(
            transcript=self._transcript, question=question
        )
        return self._call_llm(user_message)

    def _ask_rag(self, question: str) -> str:
        """RAG path: retrieve relevant chunks, send as context to LLM."""
        query_embedding = self._rag_model.encode([question]).tolist()
        results = self._rag_collection.query(
            query_embeddings=query_embedding,
            n_results=_TOP_K,
        )
        docs = results.get("documents", [[]])[0]
        chunks_text = "\n\n---\n\n".join(docs)
        user_message = _RAG_TEMPLATE.format(chunks=chunks_text, question=question)
        return self._call_llm(user_message)

    def _call_llm(self, user_message: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            return response.choices[0].message.content
        except Exception as exc:
            raise RuntimeError(f"LLM call failed: {exc}") from exc
