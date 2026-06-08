"""
Tests unitaires — MemoryService
"""
from __future__ import annotations

from unittest.mock import MagicMock, call
import pytest

from app.services.memory_service import MemoryService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_service() -> tuple[MemoryService, MagicMock]:
    db = MagicMock()
    service = MemoryService(db)
    return service, db


# ---------------------------------------------------------------------------
# Tests create_session
# ---------------------------------------------------------------------------

class TestCreateSession:

    def test_retourne_uuid_non_vide(self):
        service, db = make_service()
        session_id = service.create_session(user_id=1)
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # format UUID standard

    def test_appelle_db_create_session(self):
        service, db = make_service()
        session_id = service.create_session(user_id=42)
        db.create_session.assert_called_once_with(session_id, 42)

    def test_deux_sessions_differentes(self):
        service, db = make_service()
        s1 = service.create_session(1)
        s2 = service.create_session(1)
        assert s1 != s2


# ---------------------------------------------------------------------------
# Tests get_history
# ---------------------------------------------------------------------------

class TestGetHistory:

    def test_retourne_liste_messages(self):
        service, db = make_service()
        db.get_messages.return_value = [
            {"role": "user", "content": "Quelle souche ?"},
            {"role": "assistant", "content": "Ross 308 est recommandee."},
        ]
        history = service.get_history("uuid-test")
        assert len(history) == 2
        assert history[0]["role"] == "user"

    def test_appelle_db_avec_bon_limite(self):
        service, db = make_service()
        db.get_messages.return_value = []
        service.get_history("uuid-test")
        db.get_messages.assert_called_once_with("uuid-test", limit=20)

    def test_retourne_liste_vide_si_pas_historique(self):
        service, db = make_service()
        db.get_messages.return_value = []
        history = service.get_history("uuid-nouveau")
        assert history == []


# ---------------------------------------------------------------------------
# Tests add_message
# ---------------------------------------------------------------------------

class TestAddMessage:

    def test_appelle_db_add_message(self):
        service, db = make_service()
        service.add_message("uuid-test", "user", "Ma question")
        db.add_message.assert_called_once_with("uuid-test", "user", "Ma question")

    def test_message_assistant(self):
        service, db = make_service()
        service.add_message("uuid-test", "assistant", "Ma reponse")
        db.add_message.assert_called_once_with("uuid-test", "assistant", "Ma reponse")

    def test_appels_successifs(self):
        service, db = make_service()
        service.add_message("uuid-test", "user", "Q1")
        service.add_message("uuid-test", "assistant", "R1")
        service.add_message("uuid-test", "user", "Q2")
        assert db.add_message.call_count == 3


# ---------------------------------------------------------------------------
# Tests close_session
# ---------------------------------------------------------------------------

class TestCloseSession:

    def test_appelle_db_update_inactive(self):
        service, db = make_service()
        service.close_session("uuid-test")
        db.update_session_inactive.assert_called_once_with("uuid-test")


# ---------------------------------------------------------------------------
# Tests session_belongs_to_user
# ---------------------------------------------------------------------------

class TestSessionBelongsToUser:

    def test_session_appartient_a_utilisateur(self):
        service, db = make_service()
        db.get_session.return_value = {"id_session": "uuid", "id_utilisateur": 5, "actif": 1}
        assert service.session_belongs_to_user("uuid", 5) is True

    def test_session_appartient_a_autre_utilisateur(self):
        service, db = make_service()
        db.get_session.return_value = {"id_session": "uuid", "id_utilisateur": 5, "actif": 1}
        assert service.session_belongs_to_user("uuid", 99) is False

    def test_session_inactive(self):
        service, db = make_service()
        db.get_session.return_value = {"id_session": "uuid", "id_utilisateur": 5, "actif": 0}
        assert service.session_belongs_to_user("uuid", 5) is False

    def test_session_inexistante(self):
        service, db = make_service()
        db.get_session.return_value = None
        assert service.session_belongs_to_user("uuid-inconnu", 5) is False

    def test_id_utilisateur_en_string_accepte(self):
        service, db = make_service()
        # SQL Server peut retourner des types differents
        db.get_session.return_value = {"id_session": "uuid", "id_utilisateur": "5", "actif": 1}
        assert service.session_belongs_to_user("uuid", 5) is True