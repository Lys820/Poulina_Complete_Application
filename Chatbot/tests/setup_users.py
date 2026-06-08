"""
Script utilitaire - Génère les hash des mots de passe pour SQL Server
A exécuter une fois pour initialiser les utilisateurs de test
"""
import hashlib
import os


def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return (salt + key).hex()


users = [
    ("admin@poulina.tn",      "Admin123!"),
    ("k.bensalem@poulina.tn", "Gestionnaire123!"),
]

print("-- Copiez-collez ces UPDATE dans SQL Server Management Studio\n")
for email, pwd in users:
    h = hash_password(pwd)
    print(f"UPDATE dbo.utilisateur SET password_hash = '{h}'")
    print(f"WHERE email = '{email}';")
    print()

print("-- Mots de passe :")
for email, pwd in users:
    print(f"  {email}  =>  {pwd}")