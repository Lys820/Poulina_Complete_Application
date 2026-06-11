"""
conftest.py — Racine du projet chatbot (même niveau que main.py)

Ce fichier règle le problème "ModuleNotFoundError: No module named 'app'"
en ajoutant la racine du chatbot au sys.path avant tout import de test.

Emplacement obligatoire :
    Poulina_Complete_Application/
    └── chatbot/
        ├── conftest.py          <-- CE FICHIER
        ├── main.py
        ├── pytest.ini
        ├── app/
        │   ├── core/
        │   │   └── security.py
        │   ├── api/
        │   │   └── auth.py
        │   └── data/
        │       └── database_sqlserver.py
        └── tests/
            ├── test_security_poulelabdb.py
            ├── test_auth_endpoint_poulelabdb.py
            ├── test_database_poulelabdb.py
            ├── test_integration_poulelabdb.py
            └── test_rapide_poulelabdb.py
"""
import sys
import os

# Insère la racine du chatbot en tête du sys.path.
# os.path.dirname(__file__) = dossier contenant ce conftest.py = chatbot/
# Ainsi "from app.core.security import ..." fonctionne depuis n'importe
# quel fichier de test, quelle que soit la façon dont pytest est invoqué.
_CHATBOT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _CHATBOT_ROOT not in sys.path:
    sys.path.insert(0, _CHATBOT_ROOT)