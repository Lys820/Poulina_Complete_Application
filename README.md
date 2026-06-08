# PouleLabApp — Plateforme de Gestion des Analyses Avicoles

Application complète de gestion des demandes d'analyses en élevage avicole, intégrant un assistant IA (RAG + ML) pour la recommandation de souches et de laboratoires.

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Frontend | Angular 18+ (standalone components) |
| API métier | ASP.NET Core 10 + Entity Framework Core + Identity |
| Chatbot IA | FastAPI (Python 3.10+) + RAG + ML (scikit-learn / XGBoost) |
| Base de données | SQL Server (ODBC Driver 17) |
| Auth | JWT (Bearer Token) |
| LLM | Gemini / Claude / Mistral / OpenAI (interchangeable) |

---

## Structure du projet

```
PouleLabApp/
├── AnalyseApp/
│   ├── PouleLabApp.API/          # API REST .NET — workflow métier
│   │   ├── Controllers/          # Auth, Requests, Notifications, Users, PDF…
│   │   ├── Services/             # JWT, Email, PDF, AuditLog, DeadlineChecker…
│   │   ├── Models/               # ApplicationUser, AnalysisRequest, RequestStatus…
│   │   ├── DTOs/                 # Objets de transfert (Auth, Request, Notification…)
│   │   ├── Data/                 # ApplicationDbContext, DataSeeder
│   │   └── Program.cs            # Configuration DI, JWT, CORS, Middlewares
│   │
│   └── PouleLabApp.Frontend/     # Application Angular
│       └── src/app/
│           ├── core/
│           │   ├── services/     # AuthService, RequestService, ChatService…
│           │   ├── guards/       # authGuard, roleGuard
│           │   ├── interceptors/ # authInterceptor, errorInterceptor
│           │   └── models/       # Interfaces TypeScript
│           ├── layout/
│           │   ├── sidebar/      # Navigation filtrée par rôle
│           │   ├── header/       # Header + notifications
│           │   └── main-layout/  # Shell principal + routes
│           └── pages/
│               ├── auth/         # Login, Register
│               ├── dashboard/
│               ├── requests/     # Liste, détail, formulaire, résultats
│               ├── chat/         # Assistant IA
│               ├── notifications/
│               └── users/
│
└── Chatbot/                      # Chatbot FastAPI (microservice IA)
    ├── main.py                   # Point d'entrée FastAPI + auto-entraînement
    ├── requirements.txt
    ├── .env                      # Variables d'environnement (à créer)
    └── app/
        ├── api/                  # Endpoints : chat, analyses, souches, labos, auth…
        ├── core/                 # Config (pydantic-settings), Security (JWT/PBKDF2)
        ├── data/                 # SQLServerDB, modèles Pydantic
        ├── ml/                   # ModelFactory (RandomForest, GradientBoosting, XGBoost, Auto)
        └── services/             # RAGService, LLMService, MemoryService, RecommendationEngine
```

---

## Prérequis

- **Node.js** v18+ et `npm`
- **.NET SDK 10**
- **Python 3.10+**
- **SQL Server** (local ou distant) + ODBC Driver 17
- **Angular CLI** : `npm install -g @angular/cli`

---

## Installation et démarrage

### 1. Base de données

Créer la base SQL Server puis exécuter le script d'initialisation des tables auth et mémoire :

```bash
# Depuis SQL Server Management Studio ou sqlcmd
# Exécuter : backend/app/data/auth_memory_sqlserver.sql
```

Ensuite, appliquer les migrations EF Core pour l'API .NET :

```bash
cd AnalyseApp/PouleLabApp.API
dotnet user-secrets set "ConnectionStrings:Default" "Server=...;Database=PouleLabDb;Trusted_Connection=True;"
dotnet user-secrets set "Jwt:Secret"    "votre_secret_32_caracteres_minimum"
dotnet user-secrets set "Jwt:Issuer"    "PouleLabApp"
dotnet user-secrets set "Jwt:Audience"  "PouleLabApp"
dotnet ef database update
```

---

### 2. API .NET (port 5080)

```bash
cd AnalyseApp/PouleLabApp.API
dotnet run --launch-profile http
```

Documentation interactive disponible sur : `http://localhost:5080/scalar`

---

### 3. Chatbot IA — FastAPI (port 8000)

```bash
cd backend

# Installer les dépendances
pip install -r requirements.txt

# Créer le fichier de configuration
cp .env.example .env   # puis éditer .env avec vos clés
```

Contenu minimal du `.env` :

```env
LLM_PROVIDER=gemini
GENAI_API_KEY=votre_clé_gemini

SQLSERVER_SERVER=localhost\SQLEXPRESS
SQLSERVER_DATABASE=POULINA
SQLSERVER_USER=
SQLSERVER_PASSWORD=
SQLSERVER_TRUSTED=yes

JWT_SECRET_KEY=meme_secret_que_dotnet
```

```bash
# Lancer le serveur
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Documentation Swagger disponible sur : `http://localhost:8000/docs`

---

### 4. Frontend Angular (port 4200)

```bash
cd AnalyseApp/PouleLabApp.Frontend
npm install
ng serve
```

Application disponible sur : `http://localhost:4200`

---

## Ports récapitulatif

| Service | URL | Interface de test |
|---------|-----|-------------------|
| Frontend Angular | http://localhost:4200 | Navigateur |
| API .NET | http://localhost:5080 | `/scalar` |
| Chatbot FastAPI | http://localhost:8000 | `/docs` |

---

## Rôles et workflow

### Rôles disponibles

| Rôle | Accès |
|------|-------|
| `Administrator` | Accès total, gestion utilisateurs |
| `Manager` | Gestion utilisateurs et rapports |
| `Receptionist` | Réception et affectation des demandes |
| `Analyst` | Saisie des résultats d'analyse |
| `LabChief` | Validation des résultats |
| `Client` | Soumission et suivi de ses demandes |

### Cycle de vie d'une demande

```
Draft → Submitted → Received → Assigned → InProgress → InReview → Validated
                                                               ↘ Rejected → Received
                                                                          ↘ Closed
```

---

## Assistant IA — Chatbot

Le chatbot est un microservice Python indépendant qui expose une API REST consommée par le frontend Angular.

### Fonctionnalités

- **Recommandation de souche** via modèle ML (RandomForest / GradientBoosting / XGBoost / Auto)
- **Recommandation de laboratoire** via RAG (TF-IDF / BM25 / SentenceTransformers)
- **Alertes sanitaires** automatiques (Salmonelle, Newcastle…)
- **Mémoire conversationnelle** par session (stockée en SQL Server)
- **Multi-LLM** : Gemini (défaut), Claude, Mistral, OpenAI

### Entraînement des modèles ML

L'entraînement se fait automatiquement au démarrage si SQL Server est configuré. Il peut aussi être déclenché manuellement :

```bash
# Via l'API
POST http://localhost:8000/api/v1/analyses/train-from-sqlserver

# Ou en uploadant des CSV
POST http://localhost:8000/api/v1/analyses/upload
  → file_analyses: analyses.csv
  → file_labos: labos.csv
```

### Permissions chatbot

| Permission | Rôle | Description |
|------------|------|-------------|
| `CHAT_READ` | Tous sauf Viewer | Poser des questions |
| `CHAT_ML` | Admin, Gestionnaire | Déclencher la prédiction ML |
| `ADMIN_TRAIN` | Admin | Réentraîner les modèles |

---

## Variables d'environnement — Backend Python

| Variable | Défaut | Description |
|----------|--------|-------------|
| `LLM_PROVIDER` | `gemini` | Provider LLM actif |
| `GENAI_API_KEY` | — | Clé API Gemini |
| `ANTHROPIC_API_KEY` | — | Clé API Claude |
| `MISTRAL_API_KEY` | — | Clé API Mistral |
| `OPENAI_API_KEY` | — | Clé API OpenAI |
| `ML_MODEL` | `auto` | `random_forest` / `gradient_boosting` / `xgboost` / `auto` |
| `EMBEDDING_METHOD` | `tfidf` | `tfidf` / `bm25` / `sentence_transformers` |
| `SQLSERVER_SERVER` | — | Serveur SQL Server |
| `SQLSERVER_DATABASE` | — | Nom de la base |
| `SQLSERVER_TRUSTED` | `no` | `yes` pour auth Windows |
| `REDIS_URL` | — | Optionnel — cache Redis |
| `JWT_SECRET_KEY` | — | Doit correspondre au secret .NET |

---

## Comptes de test (après seeding)

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Administrator | admin@poulina.tn | Admin123! |
| Gestionnaire | k.bensalem@poulina.tn | Gestionnaire123! |
| Laborantin | s.labidi@poulina.tn | Laborantin123! |
| Viewer | m.trabelsi@poulina.tn | Viewer123! |

---

## Dépendances principales

### Frontend (npm)
- Angular 18+, `tslib`, `@angular/common`, `@angular/forms`, `@angular/router`

### API .NET (NuGet)
- `Microsoft.AspNetCore.Identity.EntityFrameworkCore`
- `Microsoft.EntityFrameworkCore.SqlServer`
- `Microsoft.AspNetCore.Authentication.JwtBearer`
- `QuestPDF` (génération PDF)
- `Scalar.AspNetCore` (documentation API)

### Chatbot Python (pip)
- `fastapi`, `uvicorn`, `pydantic-settings`
- `pandas`, `scikit-learn`, `xgboost`
- `PyJWT`, `pyodbc`
- `google-generativeai` / `anthropic` / `mistralai` / `openai`
