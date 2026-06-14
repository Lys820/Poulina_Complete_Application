"""
RAG Service – Embedding + Retrieval en mémoire (pas de ChromaDB local).

Le vecteur store est reconstruit en mémoire à chaque rechargement CSV.
Stratégie d'embedding interchangeable : TF-IDF (défaut), BM25, ou SentenceTransformers.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger(__name__)

# ── Champs utilisés pour transformer chaque ligne en texte (chunk) ──────────
FIELDS_ANALYSE = [
    ("id_centre", "ID centre"), ("ville", "Ville"), ("region", "Région"),
    ("type_production", "Type de production"), ("meilleure_souche", "Meilleure souche"),
    ("biosecurite_score", "Score biosécurité"), ("historique_maladie", "Historique maladie"),
    ("taux_mortalite", "Taux de mortalité"), ("fertilite_visee", "Fertilité visée"),
    ("saison", "Saison"), ("budget", "Budget"), ("temperature_moyenne", "Température"),
    ("humidite", "Humidité"), ("experience_equipe", "Expérience équipe"),
    ("conforme", "Conforme"), ("type_echantillon", "Type échantillon"),
]

FIELDS_LABO = [
    ("id_labo", "ID laboratoire"), ("nom_laboratoire", "Nom du laboratoire"),
    ("type_laboratoire", "Type"), ("ville", "Ville"), ("region", "Région"),
    ("specialites_principales", "Spécialités"), ("maladies_avicoles_traitees", "Maladies traitées"),
    ("taux_reussite_pct", "Taux de réussite"), ("note_satisfaction", "Satisfaction"),
    ("cout_analyse_moyen_tnd", "Coût (TND)"), ("cout_urgence_tnd", "Coût urgence (TND)"),
    ("delai_standard_jours", "Délai standard (j)"), ("delai_urgence_heures", "Délai urgence (h)"),
    ("accepte_urgence", "Urgences"), ("certifie_iso", "ISO"),
    ("equipement_pcr", "PCR"), ("equipement_elisa", "ELISA"),
    ("score_global", "Score global"), ("slots_disponibles_semaine", "Slots dispo"),
]


def row_to_text(row: pd.Series, fields: list[tuple[str, str]]) -> str:
    parts = []
    for col, label in fields:
        val = str(row.get(col, ""))
        if val not in ("", "nan", "N/A", "None"):
            parts.append(f"{label} : {val}.")
    return " ".join(parts)


# ────────────────────────────────────────────────────────────────────────────
# Abstract Embedder
# ────────────────────────────────────────────────────────────────────────────
class AbstractEmbedder(ABC):
    @abstractmethod
    def fit(self, texts: list[str]) -> None: ...

    @abstractmethod
    def encode(self, texts: list[str]) -> np.ndarray: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class TFIDFEmbedder(AbstractEmbedder):
    def __init__(self, max_features: int = 10_000):
        self._vec = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=2,
            analyzer="word",
        )
        self._fitted = False

    @property
    def name(self) -> str:
        return "TF-IDF"

    def fit(self, texts: list[str]) -> None:
        self._matrix = self._vec.fit_transform(texts).toarray()
        self._fitted = True

    def encode(self, texts: list[str]) -> np.ndarray:
        return self._vec.transform(texts).toarray()


class BM25Embedder(AbstractEmbedder):
    """BM25 approximé via TF-IDF pondéré. Meilleur recall sur texte court."""

    def __init__(self):
        self._vec = TfidfVectorizer(
            use_idf=True, norm="l2", sublinear_tf=False,
            ngram_range=(1, 2), min_df=1,
        )

    @property
    def name(self) -> str:
        return "BM25-approx"

    def fit(self, texts: list[str]) -> None:
        self._matrix = self._vec.fit_transform(texts).toarray()

    def encode(self, texts: list[str]) -> np.ndarray:
        return self._vec.transform(texts).toarray()


class SentenceTransformerEmbedder(AbstractEmbedder):
    """Dense embeddings multilingues. Requiert sentence-transformers."""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name)
            self._available = True
        except ImportError:
            log.warning("sentence-transformers non installé, fallback sur TF-IDF")
            self._fallback = TFIDFEmbedder()
            self._available = False

    @property
    def name(self) -> str:
        return "SentenceTransformer" if self._available else "TF-IDF(fallback)"

    def fit(self, texts: list[str]) -> None:
        if self._available:
            self._matrix = self._model.encode(texts, show_progress_bar=False)
        else:
            self._fallback.fit(texts)
            self._matrix = self._fallback._matrix

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._available:
            return self._model.encode(texts, show_progress_bar=False)
        return self._fallback.encode(texts)


def create_embedder(method: str) -> AbstractEmbedder:
    return {
        "tfidf": TFIDFEmbedder,
        "bm25": BM25Embedder,
        "sentence_transformers": SentenceTransformerEmbedder,
    }.get(method, TFIDFEmbedder)()


# ────────────────────────────────────────────────────────────────────────────
# In-Memory Vector Store
# ────────────────────────────────────────────────────────────────────────────
class InMemoryVectorStore:
    """Store vectoriel en RAM – reconstruit à chaque rechargement CSV."""

    def __init__(self, embedder: AbstractEmbedder):
        self._embedder = embedder
        self._texts: list[str] = []
        self._metadata: list[dict] = []
        self._matrix: np.ndarray | None = None

    def build(self, texts: list[str], metadata: list[dict]) -> None:
        self._texts = texts
        self._metadata = metadata
        self._embedder.fit(texts)
        self._matrix = self._embedder._matrix
        log.info("VectorStore built: %d docs [%s]", len(texts), self._embedder.name)

    def search(self, query: str, top_k: int = 5, score_threshold: float = 0.05) -> list[dict]:
        if self._matrix is None or len(self._texts) == 0:
            return []
        q_vec = self._embedder.encode([query])
        scores = cosine_similarity(q_vec, self._matrix)[0]
        top_idx = np.argsort(scores)[::-1][:top_k]
        results = []
        for i in top_idx:
            if scores[i] >= score_threshold:
                results.append({
                    "score": round(float(scores[i]), 4),
                    "text": self._texts[i],
                    "metadata": self._metadata[i],
                })
        return results


# ────────────────────────────────────────────────────────────────────────────
# RAG Service (singleton)
# ────────────────────────────────────────────────────────────────────────────
class RAGService:
    """
    Service RAG complet.
    - Reconstruit automatiquement le store quand les données changent.
    - Méthode d'embedding interchangeable via la config.
    """

    def __init__(self):
        self._store_analyses: InMemoryVectorStore | None = None
        self._store_labos: InMemoryVectorStore | None = None
        self._embedding_method: str = "tfidf"

    @property
    def is_ready(self) -> bool:
        return self._store_analyses is not None and self._store_labos is not None

    def build_from_dataframes(
        self,
        df_analyses: pd.DataFrame,
        df_labos: pd.DataFrame,
        embedding_method: str = "tfidf",
    ) -> dict:
        self._embedding_method = embedding_method

        # ── Analyses ────────────────────────────────────────────────────
        texts_a, meta_a = [], []
        for _, row in df_analyses.iterrows():
            texts_a.append(row_to_text(row, FIELDS_ANALYSE))
            meta_a.append({
                "id_centre": str(row.get("id_centre", "")),
                "ville": str(row.get("ville", "")),
                "region": str(row.get("region", "")),
                "type_production": str(row.get("type_production", "")),
                "meilleure_souche": str(row.get("meilleure_souche", "")),
                "conforme": str(row.get("conforme", "")),
                "taux_mortalite": str(row.get("taux_mortalite", "")),
            })

        store_a = InMemoryVectorStore(create_embedder(embedding_method))
        store_a.build(texts_a, meta_a)
        self._store_analyses = store_a

        # ── Labos (actifs uniquement) ────────────────────────────────────
        df_actifs = df_labos[df_labos.get("actif", pd.Series(True, index=df_labos.index)).astype(str).str.lower().isin(["true", "1", "oui"])]
        texts_l, meta_l = [], []
        for _, row in df_actifs.iterrows():
            texts_l.append(row_to_text(row, FIELDS_LABO))
            meta_l.append({
                "id_labo": str(row.get("id_labo", "")),
                "nom_laboratoire": str(row.get("nom_laboratoire", "")),
                "ville": str(row.get("ville", "")),
                "region": str(row.get("region", "")),
                "accepte_urgence": str(row.get("accepte_urgence", "")),
                "score_global": str(row.get("score_global", "")),
                "taux_reussite_pct": str(row.get("taux_reussite_pct", "")),
                "certifie_iso": str(row.get("certifie_iso", "")),
                "delai_standard_jours": str(row.get("delai_standard_jours", "")),
            })

        store_l = InMemoryVectorStore(create_embedder(embedding_method))
        store_l.build(texts_l, meta_l)
        self._store_labos = store_l

        return {
            "analyses": {"docs": len(texts_a), "embedder": store_a._embedder.name},
            "labos": {"docs": len(texts_l), "embedder": store_l._embedder.name},
        }

    # ── Keyword routing ──────────────────────────────────────────────────
    _LABO_KW = {
        "laboratoire": 2.0, "labo": 2.0, "laborantin": 1.5, "analyse": 1.2,
        "urgent": 1.5, "urgence": 1.5, "délai": 1.0, "disponible": 1.0,
        "proche": 1.0, "compétent": 1.0, "certifié": 1.0, "pcr": 1.0, "elisa": 1.0,
    }
    _SOUCHE_KW = {
        "souche": 2.0, "élevage": 1.5, "centre": 1.2, "bâtiment": 1.0,
        "fertilité": 1.0, "mortalité": 1.0, "maladie": 1.5, "salmonelle": 1.5,
        "newcastle": 1.5, "biosécurité": 1.0, "conforme": 1.0,
        "poulet": 1.0, "dinde": 1.0, "œuf": 1.0,
    }

    def _route(self, question: str) -> str:
        q = question.lower()
        s_labo = sum(w for k, w in self._LABO_KW.items() if k in q)
        s_souche = sum(w for k, w in self._SOUCHE_KW.items() if k in q)
        if s_labo > 0 and s_souche > 0:
            return "both"
        return "labos" if s_labo >= s_souche else "analyses"

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
        force: str | None = None,
        filtre_centre: str | None = None,
        filtre_ville: str | None = None,
    ) -> tuple[list[dict], list[dict]]:
        target = force or self._route(question)

        chunks_a, chunks_l = [], []

        if target in ("analyses", "both") and self._store_analyses:
            results = self._store_analyses.search(question, top_k)
            if filtre_centre:
                results = [r for r in results if r["metadata"].get("id_centre") == filtre_centre]
            chunks_a = results

        if target in ("labos", "both") and self._store_labos:
            results = self._store_labos.search(question, top_k)
            if filtre_ville:
                results = [r for r in results if r["metadata"].get("ville", "").lower() == filtre_ville.lower()]
            chunks_l = results

        return chunks_a, chunks_l


# Singleton global
rag_service = RAGService()