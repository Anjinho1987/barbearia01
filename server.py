"""
Barbearia Dom Carlo — Servidor Backend
--------------------------------------
Requisitos:
    pip install flask pymysql werkzeug

Configuração:
    1. Crie o banco de dados rodando: mysql -u root -p < schema.sql
    2. Ajuste DB_* abaixo com seus dados de acesso
    3. Rode: python server.py
    4. Acesse: http://localhost:5000

Usuarios padrão (inseridos pelo schema.sql):
    domcarlo / barbearia2024
    dev      / devadmin123
"""

import os
import json
from datetime import datetime

from flask import (
    Flask, request, jsonify, session,
    send_from_directory, abort
)
from werkzeug.security import check_password_hash
import pymysql
import pymysql.cursors

# ── CONFIGURAÇÃO ──────────────────────────────────────────────
DB_HOST     = "localhost"
DB_PORT     = 3306
DB_USER     = "root"
DB_PASSWORD = "angel19/09/1987"   # <- altere aqui
DB_NAME     = "barbearia"

SECRET_KEY  = "troque-por-uma-chave-secreta-longa-e-aleatoria"
# ──────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=".")
app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ── CONEXÃO COM O BANCO ───────────────────────────────────────

def get_db():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


# ── PÁGINAS ESTÁTICAS ─────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/dashboard")
def dashboard():
    return send_from_directory(".", "dashboard.html")


# ── AUTH ──────────────────────────────────────────────────────

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Nao autorizado"}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True) or {}
    username = (data.get("usuario") or "").strip().lower()
    senha    = (data.get("senha")   or "").strip()

    if not username or not senha:
        return jsonify({"error": "Informe usuario e senha"}), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT id, nome, senha_hash FROM usuarios WHERE username = %s",
                (username,)
            )
            user = cur.fetchone()
    finally:
        db.close()

    if not user or not check_password_hash(user["senha_hash"], senha):
        return jsonify({"error": "Usuario ou senha incorretos"}), 401

    session.permanent = True
    session["user_id"]   = user["id"]
    session["username"]  = username
    session["user_nome"] = user["nome"]

    return jsonify({"ok": True, "nome": user["nome"]})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def api_me():
    if not session.get("user_id"):
        return jsonify({"autenticado": False}), 401
    return jsonify({
        "autenticado": True,
        "nome": session.get("user_nome"),
        "username": session.get("username"),
    })


# ── PEDIDOS ───────────────────────────────────────────────────

@app.route("/api/pedidos", methods=["POST"])
def criar_pedido():
    data = request.get_json(force=True) or {}

    nome             = (data.get("nome")             or "").strip()
    whatsapp         = (data.get("whatsapp")         or "").strip()
    data_agendamento = (data.get("data_agendamento") or "").strip()
    horario          = (data.get("horario")          or "").strip()
    barbeiro         = (data.get("barbeiro")         or "").strip()
    servicos         = data.get("servicos", [])
    total            = data.get("total", 0)

    if not nome or not whatsapp or not data_agendamento or not horario:
        return jsonify({"error": "Campos obrigatorios faltando"}), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pedidos
                    (nome, whatsapp, data_agendamento, horario, barbeiro, total, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pendente')
                """,
                (nome, whatsapp, data_agendamento, horario, barbeiro, total)
            )
            pedido_id = cur.lastrowid

            for s in servicos:
                cur.execute(
                    """
                    INSERT INTO pedido_servicos (pedido_id, nome, preco, duracao)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (pedido_id, s.get("nome", ""), s.get("preco", 0), s.get("duracao", ""))
                )
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

    return jsonify({"ok": True, "id": pedido_id}), 201


@app.route("/api/pedidos", methods=["GET"])
@login_required
def listar_pedidos():
    status   = request.args.get("status",   "")
    barbeiro = request.args.get("barbeiro", "")
    busca    = request.args.get("busca",    "")

    conditions = []
    params     = []

    if status:
        conditions.append("p.status = %s")
        params.append(status)
    if barbeiro:
        conditions.append("p.barbeiro = %s")
        params.append(barbeiro)
    if busca:
        conditions.append("(p.nome LIKE %s OR p.whatsapp LIKE %s)")
        params.extend([f"%{busca}%", f"%{busca}%"])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                f"""
                SELECT p.id, p.nome, p.whatsapp, p.data_agendamento,
                       p.horario, p.barbeiro, p.total, p.status,
                       DATE_FORMAT(p.criado_em, '%d/%m/%Y %H:%i') AS data_criacao
                FROM pedidos p
                {where}
                ORDER BY p.criado_em DESC
                """,
                params
            )
            pedidos = cur.fetchall()

            # Busca serviços de cada pedido
            for p in pedidos:
                cur.execute(
                    "SELECT nome, preco, duracao FROM pedido_servicos WHERE pedido_id = %s",
                    (p["id"],)
                )
                p["servicos"] = cur.fetchall()
                p["data_agendamento"] = (
                    p["data_agendamento"].strftime("%Y-%m-%d")
                    if hasattr(p["data_agendamento"], "strftime")
                    else str(p["data_agendamento"])
                )
    finally:
        db.close()

    return jsonify(pedidos)


@app.route("/api/pedidos/<int:pedido_id>/status", methods=["PUT"])
@login_required
def atualizar_status(pedido_id):
    data   = request.get_json(force=True) or {}
    status = (data.get("status") or "").strip()

    VALIDOS = {"pendente", "confirmado", "concluido", "cancelado"}
    if status not in VALIDOS:
        return jsonify({"error": "Status invalido"}), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE pedidos SET status = %s WHERE id = %s",
                (status, pedido_id)
            )
            if cur.rowcount == 0:
                db.rollback()
                return jsonify({"error": "Pedido nao encontrado"}), 404
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

    return jsonify({"ok": True})


@app.route("/api/pedidos/<int:pedido_id>", methods=["DELETE"])
@login_required
def excluir_pedido(pedido_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("DELETE FROM pedido_servicos WHERE pedido_id = %s", (pedido_id,))
            cur.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
            if cur.rowcount == 0:
                db.rollback()
                return jsonify({"error": "Pedido nao encontrado"}), 404
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

    return jsonify({"ok": True})


# ── STATS ─────────────────────────────────────────────────────

@app.route("/api/stats")
@login_required
def api_stats():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM pedidos")
            total = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS n FROM pedidos WHERE status = 'pendente'")
            pendentes = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM pedidos WHERE status = 'confirmado'")
            confirmados = cur.fetchone()["n"]

            cur.execute(
                "SELECT COALESCE(SUM(total), 0) AS receita FROM pedidos WHERE status IN ('confirmado','concluido')"
            )
            receita = cur.fetchone()["receita"]
    finally:
        db.close()

    return jsonify({
        "total": total,
        "pendentes": pendentes,
        "confirmados": confirmados,
        "receita": float(receita),
    })


# ── MAIN ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  Barbearia Dom Carlo — Servidor")
    print("  http://localhost:5000")
    print("  http://localhost:5000/dashboard")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
