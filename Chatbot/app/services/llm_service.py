"""
LLM Service – Claude / Mistral / OpenAI / Gemini
Tous les providers supportent generate_with_history.
"""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Tu es l'assistant IA de Poulina, expert en élevage de volailles en Tunisie.
Tu analyses les données des centres d'élevage ET des laboratoires partenaires
pour aider les responsables à prendre les meilleures décisions.

## Tes capacités
- Identifier la meilleure souche pour chaque centre d'élevage (avec prédiction ML)
- Détecter et prévenir les maladies critiques (Salmonelle, Newcastle, Mycoplasme, Gumboro…)
- Recommander le meilleur laboratoire selon : distance, disponibilité, compétences, coût, urgence
- Évaluer la conformité des analyses et signaler les anomalies
- Identifier les centres potentiellement contaminés en cas de maladie critique
- Estimer la fréquence d'analyse recommandée selon la situation sanitaire
- Calculer le coût estimé d'un changement de souche

## Pour les recommandations de laboratoire, tu tiens compte de (ordre de priorité) :
1. Urgence : délai urgence et acceptation
2. Distance aux centres concernés
3. Disponibilité immédiate (slots, délai prochain RDV)
4. Compétences : spécialités, équipements PCR/ELISA/Séquençage, maladies traitées
5. Fiabilité : taux de réussite, satisfaction, années d'expérience
6. Score ML (tier Excellent / Bon / Passable)
7. Coût en TND

## Règles impératives
- Base-toi UNIQUEMENT sur le contexte fourni.
- Si l'information est absente, dis-le clairement et suggère quoi faire.
- Hors sujet : réponds exactement « Je ne peux pas répondre à cette question car elle est hors de mon domaine. »
- Sois concis et actionnable. Structure ta réponse avec des sections claires si elle est longue.
- Réponds en français.
- Pour les maladies critiques (Salmonelle, Newcastle), déclenche une alerte explicite en début de réponse.
""".strip()


class AbstractLLM(ABC):
    @abstractmethod
    async def generate(self, user_message: str, context: str) -> str: ...

    @abstractmethod
    async def generate_with_history(
        self, user_message: str, context: str, history: list[dict]
    ) -> str: ...

    @property
    @abstractmethod
    def provider(self) -> str: ...


# ── Gemini (provider par défaut) ─────────────────────────────────────────────
class GenaiLLM(AbstractLLM):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-lite"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai
        self._model_name = model

    @property
    def provider(self) -> str:
        return f"Gemini ({self._model_name})"

    async def generate(self, user_message: str, context: str) -> str:
        return await self.generate_with_history(user_message, context, [])

    async def generate_with_history(
        self, user_message: str, context: str, history: list[dict]
    ) -> str:
        import asyncio
        full_prompt = f"{SYSTEM_PROMPT}\n\nContexte (données Poulina) :\n{context}\n\n---\nQuestion : {user_message}"
        model = self._genai.GenerativeModel(self._model_name)

        # Historique au format Gemini
        chat_history = []
        for msg in history[-10:]:
            role = "user" if msg["role"] == "user" else "model"
            chat_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=chat_history)
        response = await asyncio.to_thread(chat.send_message, full_prompt)
        return response.text


# ── Claude ────────────────────────────────────────────────────────────────────
class ClaudeLLM(AbstractLLM):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def provider(self) -> str:
        return f"Claude ({self._model})"

    async def generate(self, user_message: str, context: str) -> str:
        return await self.generate_with_history(user_message, context, [])

    async def generate_with_history(
        self, user_message: str, context: str, history: list[dict]
    ) -> str:
        full_user = f"Contexte (données Poulina) :\n{context}\n\n---\nQuestion : {user_message}"
        messages = []
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": full_user})

        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return resp.content[0].text


# ── Mistral (v2.x) ────────────────────────────────────────────────────────────
class MistralLLM(AbstractLLM):
    def __init__(self, api_key: str, model: str = "mistral-large-latest"):
        try:
            from mistralai import Mistral
            self._client = Mistral(api_key=api_key)
            self._model = model
            self._available = True
        except ImportError:
            log.warning("mistralai non installé")
            self._available = False

    @property
    def provider(self) -> str:
        return f"Mistral ({self._model})" if self._available else "Mistral (unavailable)"

    async def generate(self, user_message: str, context: str) -> str:
        return await self.generate_with_history(user_message, context, [])

    async def generate_with_history(
        self, user_message: str, context: str, history: list[dict]
    ) -> str:
        if not self._available:
            raise RuntimeError("mistralai non installé : pip install mistralai")
        full_user = f"Contexte (données Poulina) :\n{context}\n\n---\nQuestion : {user_message}"
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": full_user})
        resp = await self._client.chat.complete_async(model=self._model, messages=messages)
        return resp.choices[0].message.content


# ── OpenAI ────────────────────────────────────────────────────────────────────
class OpenAILLM(AbstractLLM):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @property
    def provider(self) -> str:
        return f"OpenAI ({self._model})"

    async def generate(self, user_message: str, context: str) -> str:
        return await self.generate_with_history(user_message, context, [])

    async def generate_with_history(
        self, user_message: str, context: str, history: list[dict]
    ) -> str:
        full_user = f"Contexte (données Poulina) :\n{context}\n\n---\nQuestion : {user_message}"
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": full_user})
        resp = await self._client.chat.completions.create(
            model=self._model, messages=messages, max_tokens=1500
        )
        return resp.choices[0].message.content


# ── Factory ───────────────────────────────────────────────────────────────────
def create_llm(provider: str, settings) -> AbstractLLM:
    p = provider.lower()
    if p == "gemini" and getattr(settings, "GENAI_API_KEY", ""):
        return GenaiLLM(settings.GENAI_API_KEY, settings.GEMINI_MODEL)
    if p == "claude" and getattr(settings, "ANTHROPIC_API_KEY", ""):
        return ClaudeLLM(settings.ANTHROPIC_API_KEY)
    if p == "mistral" and getattr(settings, "MISTRAL_API_KEY", ""):
        return MistralLLM(settings.MISTRAL_API_KEY)
    if p == "openai" and getattr(settings, "OPENAI_API_KEY", ""):
        return OpenAILLM(settings.OPENAI_API_KEY)
    # Fallback automatique
    if getattr(settings, "GENAI_API_KEY", ""):
        log.warning("Fallback Gemini (provider '%s' indisponible)", provider)
        return GenaiLLM(settings.GENAI_API_KEY, settings.GEMINI_MODEL)
    if getattr(settings, "ANTHROPIC_API_KEY", ""):
        return ClaudeLLM(settings.ANTHROPIC_API_KEY)
    if getattr(settings, "MISTRAL_API_KEY", ""):
        return MistralLLM(settings.MISTRAL_API_KEY)
    if getattr(settings, "OPENAI_API_KEY", ""):
        return OpenAILLM(settings.OPENAI_API_KEY)
    raise RuntimeError(
        "Aucune clé API LLM configurée. "
        "Définir GENAI_API_KEY, ANTHROPIC_API_KEY, MISTRAL_API_KEY ou OPENAI_API_KEY dans .env"
    )
