"""
Multilingual embedder for the semantic-search classifier.

This is what actually closes the language-mismatch bug at the
representation level: unlike TF-IDF (exact token overlap, so it only ever
worked on the Hindi vocabulary it was fit on), a multilingual sentence
embedding model places semantically similar phrases from *different*
languages near each other in vector space. "tez bukhar" and "high fever"
end up close together even though they share zero characters.

Model: paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers)
  - covers 50+ languages including Hindi
  - 384-dim, small enough to run on CPU, no GPU required
  - well-established default for exactly this "same meaning, different
    language" retrieval use case

FIRST RUN NOTE: this downloads ~470MB from huggingface.co the first time
it's instantiated, then caches it locally (~/.cache/huggingface). Needs
outbound internet on whatever machine actually runs this -- it will NOT
download in a network-restricted sandbox.
"""
from __future__ import annotations
import numpy as np

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


class MultilingualEmbedder:
    def __init__(self, model_name: str = MODEL_NAME):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts) -> np.ndarray:
        """
        texts: a single string, or a list of strings.
        Returns an (n, dim) L2-normalized float32 array (or a single
        (dim,) vector if a single string was passed).
        """
        single = isinstance(texts, str)
        if single:
            texts = [texts]
        vecs = self.model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        ).astype(np.float32)
        return vecs[0] if single else vecs
