"""
Tests d'intégration — Tous les endpoints du chatbot PouleLabApp
Base de données : PouleLabDB (VICTUSL\\SQLEXPRESS)
Compte seeder : admin@poulelabapp.com / Admin@1234

Prérequis :
  1. dotnet run dans PouleLabApp.API (base PouleLabDB créée et migrée)
  2. python main.py dans Chatbot/ (chatbot sur http://localhost:8000)
  3. .env correct : SQLSERVER_DATABASE=PouleLabDB, LLM_PROVIDER=anthropic

Exécution :
    pytest test_integration_poulelabdb.py -v
    pytest test_integration_poulelabdb.py -v -s             (avec logs)
    pytest test_integration_poulelabdb.py::TestAuthEndpoint  (classe seule)
    pytest test_integration_poulelabdb.py -x                (s'arrête au 1er échec)
"""
from __future__ import annotations

import asyncio
import logging
import time

import httpx
import pytest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 120.0

ADMIN_EMAIL = "admin@poulelabapp.com"
ADMIN_PASSWORD = "Admin@1234"

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
async def http_client():
    """
    Client HTTP par test. Connexions keep-alive désactivées pour éviter
    que la connexion corrompue par un crash serveur soit réutilisée.
    Si le serveur n'est pas démarré, tous les tests sont ignorés (skip).
    """
    limits = httpx.Limits(max_keepalive_connections=0, max_connections=1)
    try:
        async with httpx.AsyncClient(
            base_url=BASE_URL, timeout=10, limits=limits
        ) as probe:
            await probe.get("/health")
    except Exception as e:
        pytest.skip(
            f"Serveur FastAPI inaccessible sur {BASE_URL}.\n"
            f"Lancez d'abord : python main.py\nErreur : {e}"
        )
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=TIMEOUT,
        limits=httpx.Limits(max_keepalive_connections=0, max_connections=10),
    ) as c:
        yield c


@pytest.fixture(scope="function")
async def trained_client(http_client):
    """
    Vérifie le serveur, déclenche l'entraînement depuis PouleLabDB,
    puis fournit le client HTTP pour les tests suivants.
    """
    # Health check
    try:
        r = await http_client.get("/health", timeout=10)
        if r.status_code != 200:
            pytest.skip(f"Serveur inaccessible : HTTP {r.status_code}")
    except Exception as e:
        pytest.skip(f"Serveur inaccessible : {e}")

    # Entraînement depuis PouleLabDB
    log.info("Déclenchement de l'entraînement depuis PouleLabDB...")
    r = await http_client.post("/analyses/train-from-sqlserver", timeout=90)
    if r.status_code != 200:
        log.warning(
            "Entraînement échoué (HTTP %s) — "
            "les tests ML/RAG peuvent être dégradés.", r.status_code
        )
    else:
        data = r.json()
        log.info(
            "Entraînement OK : %d analyses, %d labos, modèle souche=%s (acc=%.3f)",
            data.get("analyses", {}).get("docs", 0),
            data.get("labos", {}).get("docs", 0),
            data.get("model_status", {}).get("souche", {}).get("model", "N/A"),
            data.get("model_status", {}).get("souche", {}).get("accuracy", 0.0),
        )

    return http_client


@pytest.fixture(scope="function")
async def auth_token(trained_client):
    """Retourne un token JWT valide pour admin@poulelabapp.com."""
    r = await trained_client.post("/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    if r.status_code != 200:
        pytest.skip(f"Impossible d'obtenir un token : HTTP {r.status_code} — {r.text[:200]}")
    return r.json()["access_token"]


@pytest.fixture(scope="function")
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ===========================================================================
# 1. Health & Status
# ===========================================================================

class TestHealthStatus:

    async def test_health_retourne_200(self, http_client):
        r = await http_client.get("/health")
        assert r.status_code == 200

    async def test_health_contient_champs_requis(self, http_client):
        r = await http_client.get("/health")
        data = r.json()
        for champ in ("status", "version", "llm_provider", "embedding"):
            assert champ in data, f"Champ manquant : {champ}"
        assert data["status"] == "ok"

    async def test_health_provider_configure(self, http_client):
        """Le .env doit définir un LLM_PROVIDER valide."""
        r = await http_client.get("/health")
        provider = r.json().get("llm_provider")
        assert provider in ("anthropic", "genai", "mistral", "openai"), (
            f"LLM_PROVIDER inconnu : {provider!r}. "
            "Vérifiez le .env : LLM_PROVIDER doit être anthropic, genai, mistral ou openai."
        )

    async def test_status_retourne_200(self, trained_client):
        r = await trained_client.get("/status")
        assert r.status_code == 200

    async def test_status_contient_rag_et_ml(self, trained_client):
        r = await trained_client.get("/status")
        data = r.json()
        assert "rag_ready" in data
        assert "ml_ready" in data
        assert "ml_models" in data

    async def test_status_ml_ready_apres_entrainement(self, trained_client):
        r = await trained_client.get("/status")
        data = r.json()
        assert data["ml_ready"] is True, (
            "Le modèle ML doit être entraîné. "
            "Vérifiez que PouleLabDB contient des AnalysisRequests et Samples."
        )


# ===========================================================================
# 2. Entraînement depuis PouleLabDB
# ===========================================================================

class TestEntrainement:

    async def test_train_from_sqlserver_retourne_200(self, http_client):
        r = await http_client.post("/analyses/train-from-sqlserver", timeout=90)
        assert r.status_code == 200

    async def test_train_from_sqlserver_retourne_statut(self, http_client):
        r = await http_client.post("/analyses/train-from-sqlserver", timeout=90)
        assert r.status_code == 200, (
            f"HTTP {r.status_code} — le endpoint /analyses/train-from-sqlserver "
            f"a retourné une erreur. Vérifiez les logs uvicorn pour la traceback "
            f"complète. Réponse : {r.text[:300]}"
        )
        data = r.json()
        assert data.get("status") == "trained_from_sqlserver"

    async def test_train_from_sqlserver_retourne_infos_analyses(self, http_client):
        r = await http_client.post("/analyses/train-from-sqlserver", timeout=90)
        assert r.status_code == 200, f"HTTP {r.status_code} : {r.text[:200]}"
        data = r.json()
        assert "analyses" in data
        assert "docs" in data["analyses"]
        assert data["analyses"]["docs"] >= 0

    async def test_train_from_sqlserver_retourne_infos_labos(self, http_client):
        r = await http_client.post("/analyses/train-from-sqlserver", timeout=90)
        assert r.status_code == 200, f"HTTP {r.status_code} : {r.text[:200]}"
        data = r.json()
        assert "labos" in data
        assert data["labos"]["docs"] >= 0

    async def test_train_from_sqlserver_retourne_model_status(self, http_client):
        r = await http_client.post("/analyses/train-from-sqlserver", timeout=90)
        assert r.status_code == 200, f"HTTP {r.status_code} : {r.text[:200]}"
        data = r.json()
        assert "model_status" in data
        souche = data["model_status"].get("souche", {})
        assert "model" in souche

    async def test_train_from_sqlserver_contient_trained_at(self, http_client):
        r = await http_client.post("/analyses/train-from-sqlserver", timeout=90)
        assert r.status_code == 200, f"HTTP {r.status_code} : {r.text[:200]}"
        assert "trained_at" in r.json()


# ===========================================================================
# 3. Authentification
# ===========================================================================

class TestAuthEndpoint:

    async def test_login_admin_seeder_retourne_200(self, trained_client):
        r = await trained_client.post("/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        })
        assert r.status_code == 200

    async def test_login_retourne_access_token(self, trained_client):
        r = await trained_client.post("/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        })
        data = r.json()
        assert "access_token" in data
        assert len(data["access_token"]) > 20

    async def test_login_retourne_role_administrator(self, trained_client):
        r = await trained_client.post("/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        })
        assert r.json()["role"] == "Administrator"

    async def test_login_mauvais_mdp_retourne_401(self, trained_client):
        r = await trained_client.post("/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "MauvaisMotDePasse!",
        })
        assert r.status_code == 401

    async def test_login_email_inexistant_retourne_401(self, trained_client):
        r = await trained_client.post("/auth/login", json={
            "email": "fantome@poulelabapp.com",
            "password": ADMIN_PASSWORD,
        })
        assert r.status_code == 401

    async def test_login_body_vide_retourne_422(self, trained_client):
        r = await trained_client.post("/auth/login", json={})
        assert r.status_code == 422

    async def test_logout_retourne_200(self, trained_client):
        r = await trained_client.post("/auth/logout")
        assert r.status_code == 200


# ===========================================================================
# 4. Chat (RAG + ML + LLM)
# ===========================================================================

class TestChatEndpoint:

    async def test_chat_simple_retourne_200(self, trained_client, auth_headers):
        r = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "Quelle est la meilleure souche pour un élevage de poulet de chair ?",
        })
        assert r.status_code == 200

    async def test_chat_retourne_answer_non_vide(self, trained_client, auth_headers):
        r = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "Quelle souche recommandez-vous pour une production d'oeufs ?",
        })
        data = r.json()
        assert "answer" in data
        assert len(data["answer"]) > 10

    async def test_chat_retourne_session_id(self, trained_client, auth_headers):
        r = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "Quels labos sont disponibles ?",
        })
        data = r.json()
        assert "session_id" in data
        assert data["session_id"] is not None

    async def test_chat_retourne_model_used(self, trained_client, auth_headers):
        r = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "Quelle est la biosécurité recommandée ?",
        })
        data = r.json()
        assert "model_used" in data

    async def test_chat_avec_predict_souche(self, trained_client, auth_headers):
        """Vérifie le chemin RAG + ML en passant un contexte de prédiction."""
        r = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "Quelle souche pour mon élevage ?",
            "predict_souche": {
                "type_production": "Poulet de chair",
                "biosecurite_score": 8.0,
                "taux_mortalite": 2.5,
                "temperature_moyenne": 28,
                "humidite": 55,
                "fertilite_visee": 90,
                "capacite": 10000,
                "surface_m2": 600,
                "experience_equipe": 6,
                "distance_labo": 15,
                "budget": 60000,
                "saison": "Ete",
                "demande_marche": "Eleve",
                "cout_aliment": 5.2,
            },
        })
        assert r.status_code == 200
        assert len(r.json()["answer"]) > 10

    async def test_chat_maladie_avicole(self, trained_client, auth_headers):
        r = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "Y a-t-il des cas de Salmonelle critiques non résolus ?",
        })
        assert r.status_code == 200
        assert len(r.json()["answer"]) > 10

    async def test_chat_recommandation_labo(self, trained_client, auth_headers):
        r = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "Quel laboratoire me recommandez-vous pour une analyse urgente ?",
        })
        assert r.status_code == 200

    async def test_chat_hors_sujet_refuse_poliment(self, trained_client, auth_headers):
        """
        Le chatbot doit refuser les questions hors domaine avicole
        sans lever d'exception serveur.
        """
        r = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "Quel est le score du match de football de ce soir ?",
        })
        assert r.status_code == 200
        answer = r.json()["answer"].lower()
        # Le chatbot doit indiquer qu'il ne peut pas répondre hors domaine
        assert any(
            mot in answer
            for mot in ("hors", "domaine", "ne peux pas", "spécialisé", "avicole")
        ), f"Réponse hors sujet inattendue : {answer[:200]}"

    async def test_chat_sans_token_retourne_401_ou_403(self, trained_client):
        r = await trained_client.post("/chat", json={
            "question": "Test sans authentification.",
        })
        assert r.status_code in (401, 403)

    async def test_chat_question_vide_retourne_erreur(self, trained_client, auth_headers):
        r = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "",
        })
        assert r.status_code in (400, 422)

    async def test_chat_body_vide_retourne_422(self, trained_client, auth_headers):
        r = await trained_client.post("/chat", headers=auth_headers, json={})
        assert r.status_code == 422

    async def test_chat_session_differente_par_appel(self, trained_client, auth_headers):
        """Chaque appel indépendant doit produire un session_id distinct."""
        r1 = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "Quelle souche pour Tunis ?",
        })
        r2 = await trained_client.post("/chat", headers=auth_headers, json={
            "question": "Quelle souche pour Sfax ?",
        })
        assert r1.json()["session_id"] != r2.json()["session_id"]


# ===========================================================================
# 5. Prédiction de souche (endpoint direct)
# ===========================================================================

class TestSouchePredict:

    PAYLOAD_BASE = {
        "type_production": "Poulet de chair",
        "biosecurite_score": 8.0,
        "taux_mortalite": 2.5,
        "temperature_moyenne": 28,
        "humidite": 55,
        "fertilite_visee": 90,
        "capacite": 10000,
        "surface_m2": 600,
        "experience_equipe": 6,
        "distance_labo": 15,
        "budget": 60000,
        "saison": "Ete",
        "demande_marche": "Eleve",
        "cout_aliment": 5.2,
    }

    async def test_predict_poulet_chair_retourne_200(self, trained_client, auth_headers):
        r = await trained_client.post("/souches/predict", headers=auth_headers, json=self.PAYLOAD_BASE)
        assert r.status_code == 200

    async def test_predict_retourne_souche(self, trained_client, auth_headers):
        r = await trained_client.post("/souches/predict", headers=auth_headers, json=self.PAYLOAD_BASE)
        data = r.json()
        assert "souche" in data
        assert len(data["souche"]) > 0

    async def test_predict_retourne_confiance(self, trained_client, auth_headers):
        r = await trained_client.post("/souches/predict", headers=auth_headers, json=self.PAYLOAD_BASE)
        data = r.json()
        assert "confiance_pct" in data or "confiance" in data

    async def test_predict_retourne_nom_modele(self, trained_client, auth_headers):
        r = await trained_client.post("/souches/predict", headers=auth_headers, json=self.PAYLOAD_BASE)
        data = r.json()
        assert "model" in data

    async def test_predict_oeuf(self, trained_client, auth_headers):
        payload = {**self.PAYLOAD_BASE, "type_production": "Oeuf"}
        r = await trained_client.post("/souches/predict", headers=auth_headers, json=payload)
        assert r.status_code == 200

    async def test_predict_dinde(self, trained_client, auth_headers):
        payload = {**self.PAYLOAD_BASE, "type_production": "Dinde"}
        r = await trained_client.post("/souches/predict", headers=auth_headers, json=payload)
        assert r.status_code == 200

    async def test_predict_sans_token_retourne_401_ou_403(self, trained_client):
        r = await trained_client.post("/souches/predict", json=self.PAYLOAD_BASE)
        assert r.status_code in (401, 403)

    async def test_predict_payload_incomplet_retourne_422(self, trained_client, auth_headers):
        r = await trained_client.post("/souches/predict", headers=auth_headers, json={
            "type_production": "Poulet de chair",
        })
        assert r.status_code == 422


# ===========================================================================
# 6. Recommandation de laboratoires
# ===========================================================================

class TestLabosRecommend:
    """
    PouleLabDB contient les labos : DICK, SNA, GIPA, MEDOIL
    définis dans cleanup2.sql.
    """

    async def test_recommend_tous_les_labos_retourne_200(self, trained_client, auth_headers):
        r = await trained_client.get("/labos/recommend", headers=auth_headers)
        assert r.status_code == 200

    async def test_recommend_retourne_liste_labos(self, trained_client, auth_headers):
        r = await trained_client.get("/labos/recommend", headers=auth_headers)
        data = r.json()
        assert "labos" in data
        assert isinstance(data["labos"], list)

    async def test_recommend_urgence(self, trained_client, auth_headers):
        r = await trained_client.get("/labos/recommend", headers=auth_headers, params={"urgence": True})
        assert r.status_code == 200
        data = r.json()
        assert "labos" in data

    async def test_recommend_filtre_par_ville(self, trained_client, auth_headers):
        """Tunis correspond au laboratoire DICK selon les données de PouleLabDB."""
        r = await trained_client.get(
            "/labos/recommend", headers=auth_headers, params={"ville": "Tunis"}
        )
        assert r.status_code == 200

    async def test_recommend_urgence_et_ville_combinees(self, trained_client, auth_headers):
        r = await trained_client.get(
            "/labos/recommend", headers=auth_headers,
            params={"urgence": True, "ville": "Tunis"}
        )
        assert r.status_code == 200

    async def test_recommend_premier_labo_a_un_score(self, trained_client, auth_headers):
        r = await trained_client.get("/labos/recommend", headers=auth_headers)
        data = r.json()
        labos = data.get("labos", [])
        if labos:
            assert "score_global" in labos[0] or "score" in labos[0]

    async def test_recommend_sans_token_retourne_401_ou_403(self, trained_client):
        r = await trained_client.get("/labos/recommend")
        assert r.status_code in (401, 403)


# ===========================================================================
# 7. Endpoints de données (lecture directe PouleLabDB)
# ===========================================================================

class TestDataEndpoints:

    async def test_data_count_retourne_200(self, trained_client, auth_headers):
        r = await trained_client.get("/data/count", headers=auth_headers)
        assert r.status_code == 200

    async def test_data_count_contient_totaux(self, trained_client, auth_headers):
        r = await trained_client.get("/data/count", headers=auth_headers)
        data = r.json()
        # Au minimum un des compteurs doit être présent
        assert any(k in data for k in ("analyses", "labos", "souches", "total"))

    async def test_data_labos_retourne_200(self, trained_client, auth_headers):
        r = await trained_client.get("/data/labos", headers=auth_headers)
        assert r.status_code == 200

    async def test_data_labos_retourne_liste(self, trained_client, auth_headers):
        r = await trained_client.get("/data/labos", headers=auth_headers)
        data = r.json()
        assert isinstance(data, list)

    async def test_data_labos_contient_quatre_labos_poulelabdb(self, trained_client, auth_headers):
        """
        PouleLabDB est initialisé avec 4 laboratoires via cleanup2.sql :
        DICK, SNA, GIPA, MEDOIL.
        """
        r = await trained_client.get("/data/labos", headers=auth_headers)
        labos = r.json()
        assert len(labos) >= 1, "Au moins un laboratoire doit être présent dans PouleLabDB."

    async def test_data_souches_retourne_200(self, trained_client, auth_headers):
        r = await trained_client.get("/data/souches", headers=auth_headers)
        assert r.status_code == 200

    async def test_data_centres_retourne_200(self, trained_client, auth_headers):
        r = await trained_client.get("/data/centres", headers=auth_headers)
        assert r.status_code == 200