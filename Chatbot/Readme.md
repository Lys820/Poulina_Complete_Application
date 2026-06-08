# Poulina AI Chatbot – Backend FastAPI

**Architecture API-first : zéro fichier local, modèle ML interchangeable**

---

## 🚀 QUICKSTART (5 minutes)

### 1️⃣ Setup

```bash
cd backend/
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 2️⃣ Configure API keys

```bash
cp .env.example .env
# Édite .env et ajoute ta clé Anthropic :
# ANTHROPIC_API_KEY=sk-ant-...
```

### 3️⃣ Démarre le serveur

```bash
python main.py
```

Tu devrais voir :
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 4️⃣ Dans un AUTRE terminal, teste

```bash
python test_quick.py
```

Ça lance une suite de tests complète.

---

## 📋 Endpoints

### Health

```bash
GET /api/v1/health
```

### Upload CSV et entraîne ML

```bash
POST /api/v1/analyses/upload
-F "file_analyses=@analyses.csv"
-F "file_labos=@labos.csv"
```

### Chat (RAG + ML + LLM)

```bash
POST /api/v1/chat
{
  "question": "Quelle souche pour un élevage poulet chair ?",
  "predict_souche": {
    "type_production": "Poulet de chair",
    "biosecurite_score": 8.0,
    ...
  }
}
```

### Prédiction souche directe

```bash
POST /api/v1/souches/predict
{
  "type_production": "Œuf",
  "biosecurite_score": 8.0,
  ...
}
```

### Recommandation labos

```bash
GET /api/v1/labos/recommend?urgence=true&ville=Sfax
```

### Status API

```bash
GET /api/v1/status
```

---

## 🏗️ Architecture

```
backend/
├── main.py                    # FastAPI app
├── app/
│   ├── core/
│   │   └── config.py         # Settings centralisées
│   ├── ml/
│   │   └── model_factory.py  # AutoML (RF, GB, XGB) + ModelRegistry
│   ├── services/
│   │   ├── rag_service.py    # RAG (TF-IDF, BM25, SentenceTransformers)
│   │   └── llm_service.py    # LLM (Claude, Mistral, OpenAI)
│   └── api/
│       ├── health.py         # Health & status
│       ├── chat.py           # Chat endpoint
│       ├── analyses.py       # Upload CSV
│       ├── souches.py        # Prédiction souche
│       └── labos.py          # Recommandation labo
```

---

## 🔧 Configuration (.env)

```env
# ── LLM (Claude recommandé) ─────────
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=claude

# ── ML Model ────────────────────────
ML_MODEL=auto              # auto / random_forest / gradient_boosting / xgboost

# ── Embeddings ──────────────────────
EMBEDDING_METHOD=tfidf     # tfidf / bm25 / sentence_transformers
```

---

## ✨ Features clés

### ✅ ML Interchangeable

Le modèle **change facilement** sans toucher au code métier.

**Avant** (notebook v2) :
```python
rf = RandomForestClassifier()
rf.fit(X, y)
predictions = rf.predict(X_test)
```

**Maintenant** (production) :
```python
# Dans .env : ML_MODEL=auto
model = create_model("auto", num_features, cat_features)
model.fit(X, y)  # ← AutoML teste RF, GB, XGB automatiquement
```

### ✅ Zéro donnée en local

**Avant** :
```python
df = pd.read_csv("poulina_dataset_5000.csv")  # ← local
tfidf = joblib.load("./models/tfidf_analyses.pkl")  # ← local
```

**Maintenant** :
```python
# CSV uploadé via API HTTP
await client.post("/analyses/upload", files={...})
# Modèle reconstruit en mémoire (pas d'écriture disque)
```

### ✅ RAG dynamique

L'embedder change selon la config :

```env
# Rapide (CPU only)
EMBEDDING_METHOD=tfidf

# Meilleur recall sur texte court
EMBEDDING_METHOD=bm25

# Meilleure sémantique (GPU optionnel)
EMBEDDING_METHOD=sentence_transformers
```

### ✅ LLM interchangeable

Fallback automatique :

```env
LLM_PROVIDER=claude      # Essaie Claude d'abord
```

Si `ANTHROPIC_API_KEY` manque → fallback sur Mistral ou OpenAI.

---

## 📊 CSV Attendus

### `analyses.csv` (minimum)

| Colonne | Type | Exemple |
|---------|------|---------|
| id_centre | int | 1 |
| ville | str | Tunis |
| type_production | str | Poulet de chair |
| meilleure_souche | str | Cobb 500 |
| biosecurite_score | float | 8.5 |
| taux_mortalite | float | 2.1 |
| fertilite_visee | float | 92 |
| conforme | int | 1 |
| historique_maladie | str | Salmonelle |

### `labos.csv` (minimum)

| Colonne | Type | Exemple |
|---------|------|---------|
| id_labo | int | 101 |
| nom_laboratoire | str | Lab Tunis Central |
| ville | str | Tunis |
| score_global | float | 9.2 |
| accepte_urgence | int | 1 |
| delai_urgence_heures | int | 12 |
| taux_reussite_pct | float | 98 |
| tier_labo | str | Excellent |

---

## 🧪 Tests complets

Exécute le test Python complet avec:

```bash
python test_quick.py
```

Ça teste :
1. Health check
2. Upload CSV
3. Chat simple
4. Chat + prédiction ML
5. Status API
6. Recommandation labos
7. Prédiction souche directe

---

## 📈 Performance

| Opération | Temps |
|-----------|--------|
| Upload + ML training (100 lignes) | ~500ms |
| TF-IDF indexing (100 docs) | ~50ms |
| Chat question (retrieve + LLM) | ~2-3s |
| Prédiction souche (RF) | ~10ms |

---

## 🔐 Sécurité (Production)

```env
API_KEY=your-secret-key

# Headers requis
curl -H "X-Poulina-Key: your-secret-key" ...
```

En développement, laisser `API_KEY` vide = pas d'auth.

---

## 🚨 Troubleshooting

| Problème | Solution |
|----------|----------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| Connection refused | S'assurer que `python main.py` tourne |
| ML not trained | Upload CSV d'abord (`POST /analyses/upload`) |
| ANTHROPIC_API_KEY not found | Remplir `.env` |

---

## 📚 Intégration Angular

```typescript
// Angular service
export class PoulinaService {
  constructor(private http: HttpClient) {}

  chat(question: string, predictSouche?: any) {
    return this.http.post('/api/v1/chat', {
      question,
      predict_souche: predictSouche
    });
  }

  uploadCsv(analyses: File, labos: File) {
    const fd = new FormData();
    fd.append('file_analyses', analyses);
    fd.append('file_labos', labos);
    return this.http.post('/api/v1/analyses/upload', fd);
  }

  status() {
    return this.http.get('/api/v1/status');
  }
}
```

---

## 📖 Notes Architecturales

### Pourquoi pas de ChromaDB local ?

**Avant** (v2.0 notebook) :
```python
client = chromadb.PersistentClient(path="./chroma_poulina")
col.add(ids=[...], embeddings=[...], documents=[...])
```

**Maintenant** (v3.0 API) :
```python
# ChromaDB remplacé par InMemoryVectorStore
store = InMemoryVectorStore(embedder)
store.build(texts, metadata)
```

**Avantages** :
- ✅ Zéro fichier disque
- ✅ Reconstruit automatiquement si CSV change
- ✅ Embedder interchangeable (TF-IDF → BM25 → SentenceTransformers)
- ✅ Pas de dépendance lourd

### Pourquoi pas RandomForest sauvegardé ?

**Avant** (v2.0) :
```python
joblib.dump(rf_souche, "./models/rf_souche.pkl")
```

**Maintenant** (v3.0) :
```python
# Modèle reconstruit en RAM à chaque upload
model_registry.train_from_dataframes(df_analyses, df_labos, ml_model_name="auto")
```

**Avantages** :
- ✅ CSV change → modèle ré-entraîné automatiquement
- ✅ Modèle optimal change → simple swap (RF → GB → XGB)
- ✅ Zéro cache files (pas de `.pkl` à gérer)
- ✅ Prêt pour le cloud (stateless)

---

## 🎯 Next Steps

1. ✅ Backend API complète
2. ⏳ Integration Angular (composant chat)
3. ⏳ Integration Oracle DB (au lieu de CSV) - en cours
4. ⏳ WebSocket pour streaming de réponse
5. ⏳ Caching Redis pour rag + ML predictions

---

**Besoin d'aide ?** Les tests sont le meilleur doc. Lance `test_quick.py`.