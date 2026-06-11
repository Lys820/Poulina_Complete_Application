"""
Debug chat : entraîne d'abord, puis teste le chat
Credentials mis à jour : admin@poulelabapp.com / Admin@1234 (DataSeeder.cs)
"""
import requests

BASE = "http://localhost:8000/api/v1"

# ✅ Credentials du compte seedé par DataSeeder.cs
ADMIN_EMAIL    = "admin@poulelabapp.com"
ADMIN_PASSWORD = "Admin@1234"

# 1. Entraîner
print("1. Entrainement depuis SQL Server...")
r = requests.post(f"{BASE}/analyses/train-from-sqlserver")
print(f"   Status: {r.status_code}")
if r.status_code != 200:
    print(f"   Erreur: {r.text}")
    exit(1)
print("   OK")

# 2. Login
print("\n2. Login...")
r = requests.post(f"{BASE}/auth/login", json={
    "email":    ADMIN_EMAIL,
    "password": ADMIN_PASSWORD,
})
print(f"   Status: {r.status_code}")
if r.status_code != 200:
    print(f"   Erreur: {r.text}")
    exit(1)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("   OK")

# 3. Chat
print("\n3. Chat...")
r = requests.post(f"{BASE}/chat", headers=headers, json={
    "question": "Quelle est la meilleure souche a Tunis ?"
})
print(f"   Status: {r.status_code}")
print(f"   Response: {r.text[:500]}")