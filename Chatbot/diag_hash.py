import pyodbc, os, sys
from dotenv import load_dotenv
load_dotenv()
conn_str = os.getenv('SQLSERVER_CONNECTION_STRING', 'DRIVER={ODBC Driver 17 for SQL Server};Server=localhost;Database=PouleLabDB;Trusted_Connection=yes;TrustServerCertificate=yes;')
conn = pyodbc.connect(conn_str, timeout=5)
cursor = conn.cursor()
cursor.execute("SELECT NormalizedEmail, PasswordHash, LEN(PasswordHash) FROM AspNetUsers WHERE NormalizedEmail = 'ADMIN@POULELABAPP.COM'")
row = cursor.fetchone()
if row:
    print('Email     :', row[0])
    print('Hash len  :', row[2])
    print('Hash debut:', str(row[1])[:80])
    h = str(row[1])
    import base64
    raw = base64.b64decode(h)
    print('Version byte (hex):', hex(raw[0]))
    import struct
    prf, iterations, salt_len = struct.unpack_from('>III', raw, 1)
    print('PRF       :', prf, '(1=SHA256, 2=SHA512)')
    print('Iterations:', iterations)
    print('Salt len  :', salt_len)
else:
    print('Compte introuvable')
conn.close()

from app.core.security import verify_password
result = verify_password('Admin@1234', str(row[1]))
print('verify_password resultat:', result)
