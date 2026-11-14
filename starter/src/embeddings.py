"""Local embedding with sentence-transformers. Fails loudly, no mock fallback."""
from sentence_transformers import SentenceTransformer


class MyEmbedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device="cpu")
        self.dimensions = self.model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, batch_size=32, normalize_embeddings=True,
                                 show_progress_bar=True).tolist()

    def embed_query(self, question: str) -> list[float]:
        return self.model.encode(question, normalize_embeddings=True).tolist()
