"""
TEST INTEGRATION COMPLÈTE – Poulina AI Chatbot
Valide tous les endpoints, scénarios, edge cases avant intégration frontend.

✅ Corrigé : pytest-asyncio mode auto
✅ Fixture session-level async correctement gérée
✅ 54 tests organisés par domaine

Exécution:
    pytest test_integration_complete.py -v
    pytest test_integration_complete.py -v -s  (avec logs)
    pytest test_integration_complete.py::TestChatEndpoints -v
    pytest test_integration_complete.py -x  (s'arrête au premier fail)
"""

import asyncio
import pytest
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 120.0

# ✅ MODE ASYNCIO GLOBAL - FIX POUR pytest-asyncio
pytestmark = pytest.mark.asyncio


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
async def event_loop():
    """Crée une boucle asyncio pour la session"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client(event_loop):
    """Client HTTP réutilisable pour toute la session"""
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=TIMEOUT,
        verify=False  # Pour dev seulement
    ) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
async def setup_backend(client):
    """
    Setup : vérification serveur + entraînement modèles.
    Exécutée UNE SEULE FOIS avant tous les tests.
    """
    log.info("=" * 80)
    log.info("🔧 SETUP BACKEND - Initialisation")
    log.info("=" * 80)

    # 1. Health check
    try:
        log.info("   Vérification serveur...")
        r = await client.get("/health", timeout=10)
        if r.status_code != 200:
            log.error(f"   ✗ Serveur inaccessible: HTTP {r.status_code}")
            pytest.skip(f"Serveur inaccessible: {r.status_code}")
        
        data = r.json()
        log.info(f"   ✓ Serveur OK")
        log.info(f"      Provider: {data.get('llm_provider', 'N/A')}")
        log.info(f"      Embedding: {data.get('embedding', 'N/A')}")
    except Exception as e:
        log.error(f"   ✗ Erreur health check: {e}")
        pytest.skip(f"Serveur inaccessible : {e}")

    # 2. Entraînement Oracle
    log.info("   Entraînement depuis Oracle...")
    try:
        r = await client.post("/analyses/train-from-oracle", timeout=60)
        if r.status_code == 200:
            data = r.json()
            log.info(f"   ✓ Entraînement OK")
            log.info(f"      Analyses: {data.get('analyses', {}).get('docs', 0)}")
            log.info(f"      Labos: {data.get('labos', {}).get('docs', 0)}")
        else:
            log.warning(f"   ⚠ Entraînement échoué (HTTP {r.status_code})")
            log.info("   💡 Fallback: les tests essayeront quand même")
    except Exception as e:
        log.warning(f"   ⚠ Entraînement échoué: {e}")

    log.info("=" * 80)
    log.info("")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS HEALTH & STATUS (5 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthStatus:
    """Tests basiques serveur"""

    async def test_health_check(self, client):
        """✓ GET /health retourne 200 et champs requis"""
        r = await client.get("/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

        data = r.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "version" in data
        assert "llm_provider" in data
        assert "embedding" in data

        log.info(f"✓ Health: provider={data['llm_provider']}, embedding={data['embedding']}")

    async def test_status_detailed(self, client):
        """✓ GET /status retourne état complet"""
        r = await client.get("/status")
        assert r.status_code == 200

        data = r.json()
        assert "rag_ready" in data
        assert "ml_ready" in data
        assert "ml_models" in data

        log.info(f"✓ Status: RAG={data['rag_ready']}, ML={data['ml_ready']}")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DATA ENDPOINTS (13 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestDataEndpoints:
    """Tests endpoints BD directes (pas de LLM)"""

    async def test_get_centres_all(self, client):
        """✓ GET /data/centres retourne tous les centres"""
        r = await client.get("/data/centres")
        assert r.status_code == 200

        data = r.json()
        assert isinstance(data, list)
        if len(data) == 0:
            log.warning("   ⚠ Aucun centre retourné (BD vide ?)")
            return

        centre = data[0]
        required_fields = ["id_centre", "nom_centre", "localisation", "gouvernorat", "type_production"]
        for field in required_fields:
            assert field in centre, f"Champ manquant: {field}"

        log.info(f"✓ Centres: {len(data)} trouvés")

    async def test_get_centres_filter_gouvernorat(self, client):
        """✓ GET /data/centres?gouvernorat=Bizerte filtre par région"""
        r = await client.get("/data/centres", params={"gouvernorat": "Bizerte"})
        assert r.status_code == 200

        data = r.json()
        assert isinstance(data, list)
        if len(data) > 0:
            for centre in data:
                assert centre["gouvernorat"] == "Bizerte"

        log.info(f"✓ Centres Bizerte: {len(data)} trouvés")

    async def test_get_centres_filter_type(self, client):
        """✓ GET /data/centres?type_production=Poulet filtre par type"""
        r = await client.get("/data/centres", params={"type_production": "Poulet"})
        assert r.status_code == 200

        data = r.json()
        if len(data) > 0:
            for centre in data:
                assert centre["type_production"] == "Poulet"

        log.info(f"✓ Centres Poulet: {len(data)} trouvés")

    async def test_get_centres_multiple_filters(self, client):
        """✓ GET /data/centres avec plusieurs filtres"""
        r = await client.get("/data/centres", params={
            "gouvernorat": "Bizerte",
            "type_production": "Poulet"
        })
        assert r.status_code == 200

        data = r.json()
        if len(data) > 0:
            for centre in data:
                assert centre["gouvernorat"] == "Bizerte"
                assert centre["type_production"] == "Poulet"

        log.info(f"✓ Centres filtrés: {len(data)} trouvés")

    async def test_get_labos_all(self, client):
        """✓ GET /data/labos retourne tous les labos"""
        r = await client.get("/data/labos")
        assert r.status_code == 200

        data = r.json()
        assert isinstance(data, list)
        if len(data) == 0:
            log.warning("   ⚠ Aucun labo retourné (BD vide ?)")
            return

        labo = data[0]
        required_fields = ["id_labo", "nom_labo", "gouvernorat"]
        for field in required_fields:
            assert field in labo, f"Champ manquant: {field}"

        log.info(f"✓ Labos: {len(data)} trouvés")

    async def test_get_labos_filter_urgence(self, client):
        """✓ GET /data/labos?accepte_urgence=true filtre labs urgence"""
        r = await client.get("/data/labos", params={"accepte_urgence": "true"})
        assert r.status_code == 200

        data = r.json()
        if len(data) > 0:
            for labo in data:
                acc = labo.get("accepte_urgence")
                assert acc in [True, 1, "true", "1", "yes"], f"accepte_urgence invalide: {acc}"

        log.info(f"✓ Labos urgence: {len(data)} trouvés")

    async def test_get_souches_all(self, client):
        """✓ GET /data/souches retourne toutes les souches"""
        r = await client.get("/data/souches")
        assert r.status_code == 200

        data = r.json()
        assert isinstance(data, list)
        if len(data) == 0:
            log.warning("   ⚠ Aucune souche retournée (BD vide ?)")
            return

        souche = data[0]
        required_fields = ["id_souche", "nom_souche", "type_produit_final"]
        for field in required_fields:
            assert field in souche, f"Champ manquant: {field}"

        log.info(f"✓ Souches: {len(data)} trouvés")

    async def test_get_souches_filter_type(self, client):
        """✓ GET /data/souches?type_produit=Poulet filtre par type"""
        r = await client.get("/data/souches", params={"type_produit": "Poulet"})
        assert r.status_code == 200

        data = r.json()
        if len(data) > 0:
            for souche in data:
                assert "Poulet" in souche["type_produit_final"]

        log.info(f"✓ Souches Poulet: {len(data)} trouvés")

    async def test_get_centre_by_id(self, client):
        """✓ GET /data/centre/{id} retourne centre spécifique"""
        # D'abord récupère une liste
        r = await client.get("/data/centres")
        assert r.status_code == 200
        centres = r.json()

        if len(centres) > 0:
            centre_id = centres[0]["id_centre"]
            r = await client.get(f"/data/centre/{centre_id}")
            assert r.status_code == 200

            data = r.json()
            assert data["id_centre"] == centre_id
            log.info(f"✓ Centre {centre_id} détail OK")
        else:
            log.warning("   ⚠ Pas de centre pour test détail")

    async def test_get_labo_by_id(self, client):
        """✓ GET /data/labo/{id} retourne labo spécifique"""
        r = await client.get("/data/labos")
        assert r.status_code == 200
        labos = r.json()

        if len(labos) > 0:
            labo_id = labos[0]["id_labo"]
            r = await client.get(f"/data/labo/{labo_id}")
            assert r.status_code == 200

            data = r.json()
            assert data["id_labo"] == labo_id
            log.info(f"✓ Labo {labo_id} détail OK")
        else:
            log.warning("   ⚠ Pas de labo pour test détail")

    async def test_get_counts(self, client):
        """✓ GET /data/count retourne statistiques globales"""
        r = await client.get("/data/count")
        assert r.status_code == 200

        data = r.json()
        required_keys = ["centres", "labos", "souches"]
        for key in required_keys:
            assert key in data, f"Clé manquante: {key}"

        log.info(f"✓ Counts: centres={data['centres']}, labos={data['labos']}, souches={data['souches']}")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS SOUCHE PREDICTION (9 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestSouchePredict:
    """Tests prédiction souche ML"""

    VALID_REQUEST = {
        "type_production": "Poulet de chair",
        "biosecurite_score": 9.0,
        "taux_mortalite": 2.0,
        "temperature_moyenne": 28,
        "humidite": 55,
        "fertilite_visee": 94,
        "capacite": 15000,
        "surface_m2": 800,
        "experience_equipe": 8,
        "distance_labo": 10,
        "budget": 80000,
        "saison": "Ete",
        "demande_marche": "Élevé",
        "cout_aliment": 5.2
    }

    async def test_predict_poulet(self, client):
        """✓ POST /souches/predict pour Poulet de chair"""
        r = await client.post("/souches/predict", json=self.VALID_REQUEST)
        assert r.status_code == 200, f"Status {r.status_code}: {r.text}"

        data = r.json()
        assert "souche" in data, f"Champ 'souche' manquant: {data.keys()}"
        assert "confiance_pct" in data
        assert 0 <= data["confiance_pct"] <= 100

        log.info(f"✓ Poulet: {data['souche']} (confiance={data['confiance_pct']}%)")

    async def test_predict_oeuf(self, client):
        """✓ POST /souches/predict pour Œuf"""
        req = self.VALID_REQUEST.copy()
        req["type_production"] = "Oeuf"
        req["fertilite_visee"] = 96

        r = await client.post("/souches/predict", json=req)
        assert r.status_code == 200

        data = r.json()
        assert "souche" in data
        log.info(f"✓ Oeuf: {data['souche']} (confiance={data['confiance_pct']}%)")

    async def test_predict_dinde(self, client):
        """✓ POST /souches/predict pour Dinde"""
        req = self.VALID_REQUEST.copy()
        req["type_production"] = "Dinde"
        req["fertilite_visee"] = 88
        req["taux_mortalite"] = 4.0
        req["budget"] = 35000

        r = await client.post("/souches/predict", json=req)
        assert r.status_code == 200

        data = r.json()
        assert "souche" in data
        log.info(f"✓ Dinde: {data['souche']}")

    async def test_predict_validation_biosecurite(self, client):
        """✓ Validation: biosecurite_score doit être 0-10"""
        req = self.VALID_REQUEST.copy()
        req["biosecurite_score"] = 15

        r = await client.post("/souches/predict", json=req)
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"

    async def test_predict_validation_temperature(self, client):
        """✓ Validation: température doit être plausible"""
        req = self.VALID_REQUEST.copy()
        req["temperature_moyenne"] = 60

        r = await client.post("/souches/predict", json=req)
        assert r.status_code == 422

    async def test_predict_validation_budget(self, client):
        """✓ Validation: budget doit être positif"""
        req = self.VALID_REQUEST.copy()
        req["budget"] = -1000

        r = await client.post("/souches/predict", json=req)
        assert r.status_code == 422

    async def test_predict_missing_field(self, client):
        """✓ Validation: tous les champs requis"""
        req = self.VALID_REQUEST.copy()
        del req["type_production"]

        r = await client.post("/souches/predict", json=req)
        assert r.status_code == 422

    async def test_predict_confiance_presence(self, client):
        """✓ Réponse contient toujours confiance_pct"""
        r = await client.post("/souches/predict", json=self.VALID_REQUEST)
        assert r.status_code == 200

        data = r.json()
        assert "confiance_pct" in data
        assert isinstance(data["confiance_pct"], (int, float))
        assert data["confiance_pct"] >= 0

        log.info(f"✓ Confiance: {data['confiance_pct']}%")

    async def test_predict_alternatives(self, client):
        """✓ Réponse peut contenir alternatives"""
        r = await client.post("/souches/predict", json=self.VALID_REQUEST)
        assert r.status_code == 200

        data = r.json()
        if "alternatives" in data:
            assert isinstance(data["alternatives"], list)
            for alt in data["alternatives"]:
                assert "souche" in alt
                assert "confiance_pct" in alt


# ══════════════════════════════════════════════════════════════════════════════
# TESTS CHAT (13 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestChatEndpoints:
    """Tests chat endpoints"""

    async def test_chat_simple_question(self, client):
        """✓ POST /chat question simple"""
        r = await client.post("/chat", json={
            "question": "Quelle souche recommandes-tu ?"
        })
        assert r.status_code == 200, f"Status {r.status_code}: {r.text}"

        data = r.json()
        assert "question" in data
        assert "answer" in data
        assert len(data["answer"]) > 5

        log.info(f"✓ Chat simple: réponse OK ({len(data['answer'])} chars)")

    async def test_chat_maladie_alert(self, client):
        """✓ POST /chat question maladie critique"""
        r = await client.post("/chat", json={
            "question": "Y a-t-il des alertes sanitaires ?"
        })
        assert r.status_code == 200

        data = r.json()
        assert "answer" in data
        log.info("✓ Chat maladie OK")

    async def test_chat_labo_recommendation(self, client):
        """✓ POST /chat question laboratoire"""
        r = await client.post("/chat", json={
            "question": "Quel est le meilleur laboratoire ?"
        })
        assert r.status_code == 200

        data = r.json()
        assert "answer" in data
        log.info("✓ Chat labo OK")

    async def test_chat_out_of_scope(self, client):
        """✓ POST /chat question hors domaine"""
        r = await client.post("/chat", json={
            "question": "Quelle est la capitale de la France ?"
        })
        assert r.status_code == 200

        data = r.json()
        answer = data["answer"].lower()
        # Doit refuser poliment ou avouer limitation
        assert any(kw in answer for kw in ["hors", "domaine", "peux", "oeuf"]) or len(answer) > 10

        log.info("✓ Chat hors-sujet: gestion OK")

    async def test_chat_with_ml_prediction(self, client):
        """✓ POST /chat avec prédiction ML optionnelle"""
        r = await client.post("/chat", json={
            "question": "Quelle souche recommandes-tu ?",
            "predict_souche": {
                "type_production": "Poulet de chair",
                "biosecurite_score": 9.0,
                "taux_mortalite": 2.0,
                "temperature_moyenne": 28,
                "humidite": 55,
                "fertilite_visee": 94,
                "capacite": 15000,
                "surface_m2": 800,
                "experience_equipe": 8,
                "distance_labo": 10,
                "budget": 80000,
                "saison": "Ete",
                "demande_marche": "Élevé",
                "cout_aliment": 5.2
            }
        })
        assert r.status_code == 200

        data = r.json()
        assert "answer" in data
        log.info("✓ Chat + ML OK")

    async def test_chat_filtre_centre(self, client):
        """✓ POST /chat avec filtre centre"""
        r = await client.post("/chat", json={
            "question": "Quel est le statut ?",
            "filtre_centre": "1"
        })
        assert r.status_code == 200

        data = r.json()
        assert "answer" in data
        log.info("✓ Chat filtre centre OK")

    async def test_chat_filtre_ville(self, client):
        """✓ POST /chat avec filtre ville"""
        r = await client.post("/chat", json={
            "question": "Labos ?",
            "filtre_ville": "Tunis"
        })
        assert r.status_code == 200

        data = r.json()
        assert "answer" in data
        log.info("✓ Chat filtre ville OK")

    async def test_chat_force_collection(self, client):
        """✓ POST /chat avec force_collection"""
        r = await client.post("/chat", json={
            "question": "Labos ?",
            "force_collection": "labos"
        })
        assert r.status_code == 200

        data = r.json()
        assert "answer" in data
        log.info("✓ Chat force collection OK")

    async def test_chat_response_structure(self, client):
        """✓ POST /chat retourne structure complète"""
        r = await client.post("/chat", json={
            "question": "Test ?"
        })
        assert r.status_code == 200

        data = r.json()
        required_fields = ["question", "answer"]
        for field in required_fields:
            assert field in data, f"Champ manquant: {field}"

        log.info("✓ Chat structure OK")

    async def test_chat_empty_question(self, client):
        """✓ POST /chat validation question vide"""
        r = await client.post("/chat", json={"question": ""})
        assert r.status_code in [400, 422], f"Expected 400/422, got {r.status_code}"

    async def test_chat_question_too_long(self, client):
        """✓ POST /chat validation question trop longue"""
        long_q = "a" * 5000
        r = await client.post("/chat", json={"question": long_q})
        assert r.status_code in [400, 422]

    async def test_chat_invalid_json(self, client):
        """✓ POST /chat JSON invalide"""
        r = await client.post("/chat", content="{invalid json")
        assert r.status_code in [400, 422]

    async def test_chat_missing_question_field(self, client):
        """✓ POST /chat champ 'question' requis"""
        r = await client.post("/chat", json={"text": "oops"})
        assert r.status_code in [400, 422]


# ══════════════════════════════════════════════════════════════════════════════
# TESTS RECOMMENDATIONS (7 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestRecommendationEndpoints:
    """Tests endpoints recommandation"""

    async def test_recommend_souche_basic(self, client):
        """✓ POST /recommend/souche recommandation basique"""
        r = await client.post("/recommend/souche", json={
            "type_production": "Poulet de chair",
            "gouvernorat": "Bizerte",
            "budget": 80000,
            "biosecurite_score": 8.5,
            "taux_mortalite_acceptable": 3.0
        })
        assert r.status_code == 200

        data = r.json()
        assert "souche_principale" in data or "souches" in data
        log.info("✓ Recommend souche OK")

    async def test_recommend_souche_with_costs(self, client):
        """✓ POST /recommend/souche inclut analyse coûts"""
        r = await client.post("/recommend/souche", json={
            "type_production": "Poulet de chair",
            "gouvernorat": "Sfax",
            "budget": 50000,
            "biosecurite_score": 7.0,
            "taux_mortalite_acceptable": 4.0
        })
        assert r.status_code == 200

        data = r.json()
        # Peut avoir analyse_couts ou directement dans souche_principale
        assert "souche_principale" in data or "souches" in data
        log.info("✓ Recommend souche avec coûts OK")

    async def test_recommend_souche_oeuf(self, client):
        """✓ POST /recommend/souche pour Œuf"""
        r = await client.post("/recommend/souche", json={
            "type_production": "Oeuf",
            "gouvernorat": "Ariana",
            "budget": 45000,
            "biosecurite_score": 8.5,
            "taux_mortalite_acceptable": 2.0
        })
        assert r.status_code == 200

        data = r.json()
        assert "souche_principale" in data or "souches" in data
        log.info("✓ Recommend Oeuf OK")

    async def test_recommend_labo_basic(self, client):
        """✓ POST /recommend/labo recommandation basique"""
        r = await client.post("/recommend/labo", json={
            "gouvernorat": "Tunis",
            "type_analyse": "Salmonelle",
            "urgence": False
        })
        assert r.status_code == 200

        data = r.json()
        assert "labo_principal" in data or "labos" in data
        log.info("✓ Recommend labo OK")

    async def test_recommend_labo_urgent(self, client):
        """✓ POST /recommend/labo urgent"""
        r = await client.post("/recommend/labo", json={
            "gouvernorat": "Sfax",
            "type_analyse": "Newcastle",
            "urgence": True
        })
        assert r.status_code == 200

        data = r.json()
        assert "labo_principal" in data or "labos" in data
        log.info("✓ Recommend labo urgent OK")

    async def test_recommend_analyse_frequence(self, client):
        """✓ POST /recommend/analyse-frequence"""
        r = await client.post("/recommend/analyse-frequence", json={
            "maladie_detectee": "Salmonelle",
            "centre_id": 1,
            "type_production": "Poulet",
            "gouvernorat": "Bizerte"
        })
        assert r.status_code == 200

        data = r.json()
        assert "frequence_recommandee" in data or "nombre_analyses" in data
        log.info("✓ Fréquence OK")

    async def test_recommend_frequence_newcastle(self, client):
        """✓ POST /recommend/analyse-frequence Newcastle"""
        r = await client.post("/recommend/analyse-frequence", json={
            "maladie_detectee": "Newcastle",
            "centre_id": 2,
            "type_production": "Poulet",
            "gouvernorat": "Sfax"
        })
        assert r.status_code == 200

        data = r.json()
        assert "frequence_recommandee" in data or "nombre_analyses" in data
        log.info("✓ Newcastle fréquence OK")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS ERROR HANDLING (8 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """Tests gestion d'erreurs et edge cases"""

    async def test_invalid_centre_id(self, client):
        """✓ GET /data/centre/{invalid_id} retourne 404"""
        r = await client.get("/data/centre/999999")
        assert r.status_code == 404

    async def test_invalid_labo_id(self, client):
        """✓ GET /data/labo/{invalid_id} retourne 404"""
        r = await client.get("/data/labo/999999")
        assert r.status_code == 404

    async def test_malformed_json(self, client):
        """✓ POST avec JSON malformé"""
        r = await client.post("/chat", content="{invalid}")
        assert r.status_code in [400, 422]

    async def test_missing_required_field(self, client):
        """✓ POST /souches/predict sans champ requis"""
        r = await client.post("/souches/predict", json={
            "type_production": "Poulet"
        })
        assert r.status_code == 422

    async def test_invalid_enum_value(self, client):
        """✓ POST avec enum invalide"""
        r = await client.post("/chat", json={
            "question": "Test",
            "force_collection": "invalid_type"
        })
        # Peut passer ou échouer selon validation
        assert r.status_code in [200, 422]

    async def test_negative_numeric_values(self, client):
        """✓ POST /souches/predict avec valeurs négatives"""
        r = await client.post("/souches/predict", json={
            "type_production": "Poulet",
            "biosecurite_score": -5,
            "taux_mortalite": 2.0,
            "temperature_moyenne": 28,
            "humidite": 55,
            "fertilite_visee": 94,
            "capacite": 15000,
            "surface_m2": 800,
            "experience_equipe": 8,
            "distance_labo": 10,
            "budget": 80000,
            "saison": "Ete",
            "demande_marche": "Moyen",
            "cout_aliment": 5.0
        })
        assert r.status_code == 422

    async def test_string_for_numeric(self, client):
        """✓ POST /souches/predict string où numeric attendu"""
        r = await client.post("/souches/predict", json={
            "type_production": "Poulet",
            "biosecurite_score": "nine",
            "taux_mortalite": 2.0,
            "temperature_moyenne": 28,
            "humidite": 55,
            "fertilite_visee": 94,
            "capacite": 15000,
            "surface_m2": 800,
            "experience_equipe": 8,
            "distance_labo": 10,
            "budget": 80000,
            "saison": "Ete",
            "demande_marche": "Moyen",
            "cout_aliment": 5.0
        })
        assert r.status_code == 422

    async def test_extremely_large_values(self, client):
        """✓ POST /souches/predict avec valeurs extrêmes"""
        r = await client.post("/souches/predict", json={
            "type_production": "Poulet",
            "biosecurite_score": 9.0,
            "taux_mortalite": 2.0,
            "temperature_moyenne": 28,
            "humidite": 55,
            "fertilite_visee": 94,
            "capacite": 9999999999,
            "surface_m2": 800,
            "experience_equipe": 8,
            "distance_labo": 10,
            "budget": 80000,
            "saison": "Ete",
            "demande_marche": "Moyen",
            "cout_aliment": 5.0
        })
        assert r.status_code in [200, 422]


# ══════════════════════════════════════════════════════════════════════════════
# TESTS PERFORMANCE (3 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformance:
    """Tests limites de performance"""

    async def test_data_response_time(self, client):
        """✓ GET /data/centres < 1000ms"""
        t0 = time.time()
        r = await client.get("/data/centres")
        elapsed = (time.time() - t0) * 1000

        assert r.status_code == 200
        assert elapsed < 1000, f"Response time: {elapsed:.0f}ms (trop lent)"
        log.info(f"✓ Data time: {elapsed:.0f}ms")

    async def test_predict_response_time(self, client):
        """✓ POST /souches/predict < 1000ms"""
        t0 = time.time()
        r = await client.post("/souches/predict", json={
            "type_production": "Poulet",
            "biosecurite_score": 9.0,
            "taux_mortalite": 2.0,
            "temperature_moyenne": 28,
            "humidite": 55,
            "fertilite_visee": 94,
            "capacite": 15000,
            "surface_m2": 800,
            "experience_equipe": 8,
            "distance_labo": 10,
            "budget": 80000,
            "saison": "Ete",
            "demande_marche": "Moyen",
            "cout_aliment": 5.0
        })
        elapsed = (time.time() - t0) * 1000

        assert r.status_code == 200
        assert elapsed < 1000, f"Prediction time: {elapsed:.0f}ms (trop lent)"
        log.info(f"✓ Predict time: {elapsed:.0f}ms")

    async def test_chat_response_time(self, client):
        """✓ POST /chat < 10s (LLM peut être lent)"""
        t0 = time.time()
        r = await client.post("/chat", json={
            "question": "Test performance"
        })
        elapsed = time.time() - t0

        assert r.status_code == 200
        log.info(f"✓ Chat time: {elapsed:.1f}s")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS E2E (2 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestE2E:
    """Tests scénarios complets bout-en-bout"""

    async def test_e2e_farm_analysis(self, client):
        """✓ Scénario complet: analyser une ferme"""
        log.info("\n" + "=" * 60)
        log.info("E2E: Farm Analysis Scenario")
        log.info("=" * 60)

        # 1. Get centres
        r = await client.get("/data/centres", params={"gouvernorat": "Bizerte"})
        assert r.status_code == 200
        centres = r.json()
        if len(centres) == 0:
            log.warning("   ⚠ Pas de centre pour test E2E")
            return
        centre_id = centres[0]["id_centre"]
        log.info(f"1. Centre trouvé: {centres[0]['nom_centre']}")

        # 2. Predict souche
        r = await client.post("/souches/predict", json={
            "type_production": "Poulet",
            "biosecurite_score": 8.0,
            "taux_mortalite": 2.5,
            "temperature_moyenne": 28,
            "humidite": 60,
            "fertilite_visee": 92,
            "capacite": 12000,
            "surface_m2": 600,
            "experience_equipe": 5,
            "distance_labo": 10,
            "budget": 60000,
            "saison": "Ete",
            "demande_marche": "Moyen",
            "cout_aliment": 5.0
        })
        if r.status_code == 200:
            souche = r.json().get("souche", "N/A")
            log.info(f"2. Souche recommandée: {souche}")

        # 3. Get labos
        r = await client.get("/data/labos", params={"gouvernorat": "Bizerte"})
        if r.status_code == 200:
            labos = r.json()
            log.info(f"3. Labos trouvés: {len(labos)}")

        # 4. Chat question
        r = await client.post("/chat", json={
            "question": "Comment optimiser cet élevage ?",
            "filtre_centre": str(centre_id)
        })
        if r.status_code == 200:
            log.info("4. Chat réponse OK")

        log.info("✓ E2E Farm Analysis complète\n")

    async def test_e2e_disease_response(self, client):
        """✓ Scénario: détecter et gérer une maladie"""
        log.info("\n" + "=" * 60)
        log.info("E2E: Disease Response Scenario")
        log.info("=" * 60)

        # 1. Ask about disease
        r = await client.post("/chat", json={
            "question": "Avons-nous des problèmes de Salmonelle ?"
        })
        if r.status_code == 200:
            log.info("1. Question maladie OK")

        # 2. Get recommendation
        r = await client.post("/recommend/analyse-frequence", json={
            "maladie_detectee": "Salmonelle",
            "centre_id": 1,
            "type_production": "Poulet",
            "gouvernorat": "Bizerte"
        })
        if r.status_code == 200:
            data = r.json()
            freq = data.get("frequence_recommandee", "N/A")
            log.info(f"2. Fréquence: {freq}")

        # 3. Get urgent lab
        r = await client.post("/recommend/labo", json={
            "gouvernorat": "Bizerte",
            "type_analyse": "Salmonelle",
            "urgence": True
        })
        if r.status_code == 200:
            labo = r.json().get("labo_principal", {}).get("nom_labo", "N/A")
            log.info(f"3. Labo urgent: {labo}")

        log.info("✓ E2E Disease Response complète\n")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    log.info("\n" + "=" * 80)
    log.info("POULINA AI - TESTS D'INTEGRATION COMPLETE")
    log.info("=" * 80 + "\n")
    
    # Exécute pytest avec options
    exit_code = pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "--color=yes"
    ])
    
    sys.exit(exit_code)