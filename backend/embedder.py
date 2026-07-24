from __future__ import annotations
import numpy as np

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

class MultilingualEmbedder:
    def __init__(self, model_name: str = MODEL_NAME):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts) -> np.ndarray:
        single = isinstance(texts, str)
        if single:
            texts = [texts]
        vecs = self.model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        ).astype(np.float32)
        return vecs[0] if single else vecs