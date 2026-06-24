"""
Rode este script UMA VEZ para gerar os hashes corretos
e inserir os usuarios no banco de dados.

    python gerar_senhas.py
"""

from werkzeug.security import generate_password_hash
import pymysql

DB_HOST     = "localhost"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = "angel19/09/1987"   # <- igual ao server.py
DB_NAME     = "barbearia"

USUARIOS = [
    {"username": "domcarlo", "nome": "Dom Carlo (Dono)",  "senha": "barbearia2024"},
    {"username": "dev",      "nome": "Desenvolvedor",     "senha": "devadmin123"},
]

def main():
    db = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4"
    )
    try:
        with db.cursor() as cur:
            for u in USUARIOS:
                h = generate_password_hash(u["senha"])
                cur.execute(
                    """
                    INSERT INTO usuarios (username, nome, senha_hash)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE nome = VALUES(nome), senha_hash = VALUES(senha_hash)
                    """,
                    (u["username"], u["nome"], h)
                )
                print(f"  OK: {u['username']} / {u['senha']}")
        db.commit()
        print("\nUsuarios inseridos com sucesso!")
        print("Agora rode: python server.py")
    finally:
        db.close()

if __name__ == "__main__":
    main()
