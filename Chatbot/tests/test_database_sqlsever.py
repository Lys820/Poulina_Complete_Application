"""
Tests unitaires — SQLServerDB
Pas de connexion reelle : toute dependance pyodbc est mockee.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch, call
import pytest
import pandas as pd

# ---------------------------------------------------------------------------
# Mock de pyodbc avant tout import du module a tester
# ---------------------------------------------------------------------------
pyodbc_mock = types.ModuleType("pyodbc")
pyodbc_mock.connect = MagicMock()
pyodbc_mock.Connection = MagicMock
pyodbc_mock.Error = Exception
sys.modules["pyodbc"] = pyodbc_mock


from app.data.database_sqlserver import SQLServerDB, get_db  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_db() -> SQLServerDB:
    return SQLServerDB(
        server="localhost",
        database="POULINA",
        user="sa",
        password="Test1234!",
    )


def mock_conn_with_rows(columns: list[str], rows: list[tuple]) -> MagicMock:
    """Retourne un mock de connexion qui renvoie les lignes donnees."""
    cursor = MagicMock()
    cursor.description = [(col, None, None, None, None, None, None) for col in columns]
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = rows[0] if rows else None

    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# ---------------------------------------------------------------------------
# Tests connexion
# ---------------------------------------------------------------------------

class TestConnexion:

    def test_connect_succes(self):
        db = make_db()
        pyodbc_mock.connect.return_value = MagicMock()
        result = db.connect()
        assert result is True
        assert db._conn is not None

    def test_connect_echec_renvoie_false(self):
        db = make_db()
        with patch("app.data.database_sqlserver.pyodbc") as mock_pyodbc:
            mock_pyodbc.connect.side_effect = Exception("Connection refused")
            result = db.connect()
        assert result is False

    def test_close_appelle_close_sur_connexion(self):
        db = make_db()
        db._conn = MagicMock()
        db.close()
        db._conn.close.assert_called_once()

    def test_close_sans_connexion_ne_plante_pas(self):
        db = make_db()
        db._conn = None
        db.close()  # ne doit pas lever d exception


# ---------------------------------------------------------------------------
# Tests get_analyses_data
# ---------------------------------------------------------------------------

class TestGetAnalysesData:

    COLUMNS = [
        "id_demande", "num_analyse", "id_centre", "nom_centre", "ville",
        "region", "type_production", "id_batiment", "nom_batiment",
        "id_souche", "meilleure_souche", "fertilite_visee", "taux_mortalite",
        "resistance_maladies", "type_analyse", "libelle_analyse",
        "type_echantillon", "date_prelevement", "date_analyse", "date_resultat",
        "priorite", "conforme", "pourcentage_securite", "statut",
        "resultat_souche_detectee", "niveau_satisfaction", "nom_labo",
        "labo_gouvernorat", "nom_laborantin", "specialite_laborantin",
        "pays_provenance", "saison", "capacite", "cout_aliment",
        "temperature_moyenne", "humidite", "biosecurite_score",
        "experience_equipe", "distance_labo", "budget",
        "historique_maladie", "maladie_critique",
    ]

    def test_retourne_dataframe(self):
        db = make_db()
        row = tuple([1, "ANA-001", 1, "Centre A"] + [None] * (len(self.COLUMNS) - 4))
        conn, _ = mock_conn_with_rows(self.COLUMNS, [row])
        db._conn = conn
        df = db.get_analyses_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_colonnes_presentes(self):
        db = make_db()
        row = tuple([1, "ANA-001", 1, "Centre A"] + [None] * (len(self.COLUMNS) - 4))
        conn, _ = mock_conn_with_rows(self.COLUMNS, [row])
        db._conn = conn
        df = db.get_analyses_data()
        assert "meilleure_souche" in df.columns
        assert "conforme" in df.columns

    def test_retourne_df_vide_si_erreur_sql(self):
        db = make_db()
        conn = MagicMock()
        conn.cursor.side_effect = Exception("SQL error")
        db._conn = conn
        df = db.get_analyses_data()
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_plusieurs_lignes(self):
        db = make_db()
        rows = [
            tuple([i, f"ANA-{i:03d}", i, f"Centre {i}"] + [None] * (len(self.COLUMNS) - 4))
            for i in range(1, 6)
        ]
        conn, _ = mock_conn_with_rows(self.COLUMNS, rows)
        db._conn = conn
        df = db.get_analyses_data()
        assert len(df) == 5


# ---------------------------------------------------------------------------
# Tests get_labos_data
# ---------------------------------------------------------------------------

class TestGetLabosData:

    COLUMNS = [
        "id_labo", "nom_laboratoire", "ville", "region", "latitude",
        "longitude", "telephone", "email", "actif", "nb_laborantins",
        "taux_reussite_pct", "nb_analyses_effectuees", "delai_standard_jours",
        "delai_urgence_heures", "accepte_urgence", "certifie_iso",
        "equipement_pcr", "equipement_elisa", "annees_experience_labo",
        "score_global", "tier_labo", "type_laboratoire",
        "specialites_principales", "maladies_avicoles_traitees",
    ]

    def test_retourne_dataframe(self):
        db = make_db()
        row = (1, "Labo Central", "Tunis") + (None,) * (len(self.COLUMNS) - 3)
        conn, _ = mock_conn_with_rows(self.COLUMNS, [row])
        db._conn = conn
        df = db.get_labos_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_colonne_score_global_presente(self):
        db = make_db()
        row = (1, "Labo Central", "Tunis") + (None,) * (len(self.COLUMNS) - 3)
        conn, _ = mock_conn_with_rows(self.COLUMNS, [row])
        db._conn = conn
        df = db.get_labos_data()
        assert "score_global" in df.columns

    def test_retourne_df_vide_si_erreur(self):
        db = make_db()
        conn = MagicMock()
        conn.cursor.side_effect = Exception("SQL error")
        db._conn = conn
        df = db.get_labos_data()
        assert df.empty


# ---------------------------------------------------------------------------
# Tests get_utilisateur_par_email
# ---------------------------------------------------------------------------

class TestGetUtilisateurParEmail:

    COLUMNS = [
        "id_utilisateur", "password_hash", "nom", "prenom",
        "actif", "nom_role", "permissions",
    ]

    def test_retourne_dict_si_trouve(self):
        db = make_db()
        row = (1, "hash123", "Bouaziz", "Sami", 1, "ADMIN", "CHAT_READ,CHAT_ML")
        conn, cursor = mock_conn_with_rows(self.COLUMNS, [row])
        db._conn = conn
        result = db.get_utilisateur_par_email("sami@poulina.tn")
        assert result is not None
        assert result["nom_role"] == "ADMIN"
        assert result["permissions"] == "CHAT_READ,CHAT_ML"

    def test_retourne_none_si_absent(self):
        db = make_db()
        conn, cursor = mock_conn_with_rows(self.COLUMNS, [])
        cursor.fetchone.return_value = None
        db._conn = conn
        result = db.get_utilisateur_par_email("inconnu@poulina.tn")
        assert result is None


# ---------------------------------------------------------------------------
# Tests session
# ---------------------------------------------------------------------------

class TestSession:

    def test_create_session_insere_et_commit(self):
        db = make_db()
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        db._conn = conn

        db.create_session("uuid-test", user_id=42)

        assert cursor.execute.call_count == 1
        conn.commit.assert_called_once()

    def test_get_session_existante(self):
        db = make_db()
        cursor = MagicMock()
        cursor.description = [
            ("id_session", None), ("id_utilisateur", None), ("actif", None)
        ]
        cursor.fetchone.return_value = ("uuid-test", 42, 1)
        conn = MagicMock()
        conn.cursor.return_value = cursor
        db._conn = conn

        session = db.get_session("uuid-test")
        assert session is not None
        assert session["id_utilisateur"] == 42
        assert session["actif"] == 1

    def test_get_session_absente_retourne_none(self):
        db = make_db()
        cursor = MagicMock()
        cursor.description = [
            ("id_session", None), ("id_utilisateur", None), ("actif", None)
        ]
        cursor.fetchone.return_value = None
        conn = MagicMock()
        conn.cursor.return_value = cursor
        db._conn = conn

        session = db.get_session("uuid-inexistant")
        assert session is None

    def test_add_message_execute_deux_requetes(self):
        db = make_db()
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        db._conn = conn

        db.add_message("uuid-test", "user", "Quelle souche ?")

        assert cursor.execute.call_count == 2
        conn.commit.assert_called_once()

    def test_get_messages_retourne_liste(self):
        db = make_db()
        cursor = MagicMock()
        cursor.fetchall.return_value = [("user", "Bonjour"), ("assistant", "Bonjour !")]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        db._conn = conn

        messages = db.get_messages("uuid-test", limit=10)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_update_session_inactive(self):
        db = make_db()
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        db._conn = conn

        db.update_session_inactive("uuid-test")
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Tests get_db factory
# ---------------------------------------------------------------------------

class TestGetDb:

    def test_get_db_retourne_instance(self):
        settings = MagicMock()
        settings.SQLSERVER_SERVER = "localhost"
        settings.SQLSERVER_DATABASE = "POULINA"
        settings.SQLSERVER_USER = "sa"
        settings.SQLSERVER_PASSWORD = "pwd"
        settings.SQLSERVER_DRIVER = "ODBC Driver 17 for SQL Server"

        db = get_db(settings)
        assert isinstance(db, SQLServerDB)
        assert db.server == "localhost"
        assert db.database == "POULINA"

    def test_get_db_driver_par_defaut(self):
        settings = MagicMock()
        settings.SQLSERVER_SERVER = "localhost"
        settings.SQLSERVER_DATABASE = "POULINA"
        settings.SQLSERVER_USER = "sa"
        settings.SQLSERVER_PASSWORD = "pwd"
        del settings.SQLSERVER_DRIVER
        settings.SQLSERVER_DRIVER = "ODBC Driver 17 for SQL Server"

        db = get_db(settings)
        assert "ODBC Driver 17" in db.driver


# ---------------------------------------------------------------------------
# Tests get_all_data
# ---------------------------------------------------------------------------

class TestGetAllData:

    def test_get_all_data_appelle_les_deux_requetes(self):
        db = make_db()
        db._conn = MagicMock()

        with patch.object(db, "get_analyses_data", return_value=pd.DataFrame({"a": [1]})) as mock_a, \
             patch.object(db, "get_labos_data", return_value=pd.DataFrame({"b": [2]})) as mock_l:
            df_a, df_l = db.get_all_data()

        mock_a.assert_called_once()
        mock_l.assert_called_once()
        assert not df_a.empty
        assert not df_l.empty

    def test_get_all_data_connexion_echoue_retourne_vide(self):
        db = make_db()
        db._conn = None
        with patch("app.data.database_sqlserver.pyodbc") as mock_pyodbc:
            mock_pyodbc.connect.side_effect = Exception("refused")
            df_a, df_l = db.get_all_data()
        assert df_a.empty
        assert df_l.empty