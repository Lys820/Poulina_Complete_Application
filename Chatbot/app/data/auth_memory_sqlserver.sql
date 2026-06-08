-- ============================================================
-- POULINA — TABLES AUTHENTIFICATION ET MEMOIRE CONVERSATIONNELLE
-- SQL Server 2019+
-- A executer sur la base POULINA existante
-- ============================================================

USE [POULINA];
GO

-- ============================================================
-- DROP dans l'ordre inverse des FK
-- ============================================================

IF OBJECT_ID('dbo.message_chat',   'U') IS NOT NULL DROP TABLE dbo.message_chat;
IF OBJECT_ID('dbo.session_chat',   'U') IS NOT NULL DROP TABLE dbo.session_chat;
IF OBJECT_ID('dbo.role_permission','U') IS NOT NULL DROP TABLE dbo.role_permission;
IF OBJECT_ID('dbo.utilisateur',    'U') IS NOT NULL DROP TABLE dbo.utilisateur;
IF OBJECT_ID('dbo.permission',     'U') IS NOT NULL DROP TABLE dbo.permission;
IF OBJECT_ID('dbo.role',           'U') IS NOT NULL DROP TABLE dbo.role;
GO

-- ============================================================
-- ROLE
-- ============================================================

CREATE TABLE dbo.role (
    id_role     INT IDENTITY(1,1) PRIMARY KEY,
    nom_role    NVARCHAR(50)  UNIQUE NOT NULL,
    description NVARCHAR(200)
);
GO

-- ============================================================
-- PERMISSION
-- ============================================================

CREATE TABLE dbo.permission (
    id_permission   INT IDENTITY(1,1) PRIMARY KEY,
    code            NVARCHAR(100) UNIQUE NOT NULL,
    description     NVARCHAR(200)
);
GO

-- ============================================================
-- ROLE_PERMISSION
-- ============================================================

CREATE TABLE dbo.role_permission (
    id_role         INT NOT NULL,
    id_permission   INT NOT NULL,
    PRIMARY KEY (id_role, id_permission),
    CONSTRAINT fk_rp_role FOREIGN KEY (id_role)
        REFERENCES dbo.role(id_role),
    CONSTRAINT fk_rp_perm FOREIGN KEY (id_permission)
        REFERENCES dbo.permission(id_permission)
);
GO

-- ============================================================
-- UTILISATEUR
-- ============================================================

CREATE TABLE dbo.utilisateur (
    id_utilisateur  INT IDENTITY(1,1) PRIMARY KEY,
    nom             NVARCHAR(100) NOT NULL,
    prenom          NVARCHAR(100) NOT NULL,
    email           NVARCHAR(150) UNIQUE NOT NULL,
    password_hash   NVARCHAR(256) NOT NULL,
    id_role         INT NOT NULL,
    id_filiale      INT,
    actif           BIT DEFAULT 1,
    date_creation   DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_user_role    FOREIGN KEY (id_role)
        REFERENCES dbo.role(id_role),
    CONSTRAINT fk_user_filiale FOREIGN KEY (id_filiale)
        REFERENCES dbo.filiale(id_filiale)
);
GO

-- ============================================================
-- SESSION_CHAT
-- ============================================================

CREATE TABLE dbo.session_chat (
    id_session              NVARCHAR(64) PRIMARY KEY,
    id_utilisateur          INT NOT NULL,
    date_debut              DATETIME2 DEFAULT GETDATE(),
    date_derniere_activite  DATETIME2 DEFAULT GETDATE(),
    actif                   BIT DEFAULT 1,
    contexte_json           NVARCHAR(MAX) DEFAULT '{}',
    CONSTRAINT fk_session_user FOREIGN KEY (id_utilisateur)
        REFERENCES dbo.utilisateur(id_utilisateur)
);
GO

-- ============================================================
-- MESSAGE_CHAT
-- ============================================================

CREATE TABLE dbo.message_chat (
    id_message      INT IDENTITY(1,1) PRIMARY KEY,
    id_session      NVARCHAR(64) NOT NULL,
    role            NVARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    contenu         NVARCHAR(MAX) NOT NULL,
    date_message    DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT fk_msg_session FOREIGN KEY (id_session)
        REFERENCES dbo.session_chat(id_session)
);
GO

-- ============================================================
-- DONNEES REFERENTIELLES
-- ============================================================

-- Roles
INSERT INTO dbo.role (nom_role, description) VALUES
    ('ADMIN',        'Administrateur : acces complet'),
    ('GESTIONNAIRE', 'Gestionnaire analyses et elevages'),
    ('LABORANTIN',   'Personnel laboratoire'),
    ('VIEWER',       'Consultation uniquement');
GO

-- Permissions
INSERT INTO dbo.permission (code, description) VALUES
    ('CHAT_READ',       'Poser des questions au chatbot'),
    ('CHAT_ML',         'Declencher des predictions ML'),
    ('ANALYSE_CREATE',  'Creer une demande d analyse'),
    ('ANALYSE_READ',    'Consulter les analyses'),
    ('LABO_READ',       'Consulter les laboratoires'),
    ('SOUCHE_READ',     'Consulter les souches'),
    ('ADMIN_TRAIN',     'Reentrainer les modeles'),
    ('ADMIN_USERS',     'Gerer les utilisateurs');
GO

-- Attribution permissions par role
-- ADMIN : tout
INSERT INTO dbo.role_permission (id_role, id_permission)
SELECT r.id_role, p.id_permission
FROM dbo.role r, dbo.permission p
WHERE r.nom_role = 'ADMIN';

-- GESTIONNAIRE
INSERT INTO dbo.role_permission (id_role, id_permission)
SELECT r.id_role, p.id_permission
FROM dbo.role r
JOIN dbo.permission p ON p.code IN (
    'CHAT_READ', 'CHAT_ML',
    'ANALYSE_CREATE', 'ANALYSE_READ',
    'LABO_READ', 'SOUCHE_READ'
)
WHERE r.nom_role = 'GESTIONNAIRE';

-- LABORANTIN
INSERT INTO dbo.role_permission (id_role, id_permission)
SELECT r.id_role, p.id_permission
FROM dbo.role r
JOIN dbo.permission p ON p.code IN (
    'CHAT_READ',
    'ANALYSE_CREATE', 'ANALYSE_READ',
    'LABO_READ', 'SOUCHE_READ'
)
WHERE r.nom_role = 'LABORANTIN';

-- VIEWER
INSERT INTO dbo.role_permission (id_role, id_permission)
SELECT r.id_role, p.id_permission
FROM dbo.role r
JOIN dbo.permission p ON p.code IN (
    'CHAT_READ',
    'ANALYSE_READ',
    'LABO_READ', 'SOUCHE_READ'
)
WHERE r.nom_role = 'VIEWER';
GO

-- ============================================================
-- UTILISATEURS DE TEST
-- Le password_hash correspond a "Admin123!" encode en PBKDF2
-- A remplacer par de vrais hash generes par l'application
-- ============================================================

-- Mot de passe par defaut : Admin123!
-- Le hash reel sera genere par security.py au premier lancement
-- Ces valeurs sont des placeholders a remplacer
INSERT INTO dbo.utilisateur (nom, prenom, email, password_hash, id_role, id_filiale, actif)
SELECT 'Administrateur', 'Poulina', 'admin@poulina.tn',
       'PLACEHOLDER_HASH_A_REMPLACER',
       r.id_role, 1, 1
FROM dbo.role r WHERE r.nom_role = 'ADMIN';

INSERT INTO dbo.utilisateur (nom, prenom, email, password_hash, id_role, id_filiale, actif)
SELECT 'Ben Salem', 'Karim', 'k.bensalem@poulina.tn',
       'PLACEHOLDER_HASH_A_REMPLACER',
       r.id_role, 1, 1
FROM dbo.role r WHERE r.nom_role = 'GESTIONNAIRE';
GO

-- ============================================================
-- INDEX PERFORMANCES
-- ============================================================

CREATE INDEX idx_session_user     ON dbo.session_chat(id_utilisateur);
CREATE INDEX idx_session_actif    ON dbo.session_chat(actif);
CREATE INDEX idx_message_session  ON dbo.message_chat(id_session, date_message);
CREATE INDEX idx_user_email       ON dbo.utilisateur(email);
GO

PRINT 'Tables auth et memoire creees avec succes.';
GO