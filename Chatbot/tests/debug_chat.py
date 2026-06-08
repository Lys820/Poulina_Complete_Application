"""
Debug chat : entraîne d'abord, puis teste le chat
"""
import requests

BASE = "http://localhost:8000/api/v1"

# 1. Entraîner
print("1. Entraînement depuis SQL Server...")
r = requests.post(f"{BASE}/analyses/train-from-sqlserver")
print(f"   Status: {r.status_code}")
if r.status_code != 200:
    print(f"   Erreur: {r.text}")
    exit(1)
print("   OK")

# 2. Login
print("\n2. Login...")
r = requests.post(f"{BASE}/auth/login", json={"email": "admin@poulina.tn", "password": "Admin123!"})
print(f"   Status: {r.status_code}")
if r.status_code != 200:
    print(f"   Erreur: {r.text}")
    exit(1)
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("   OK")

# 3. Chat
print("\n3. Chat...")
r = requests.post(f"{BASE}/chat", headers=headers, json={"question": "Quelle est la meilleure souche à Tunis ?"})
print(f"   Status: {r.status_code}")
print(f"   Response: {r.text[:500]}")