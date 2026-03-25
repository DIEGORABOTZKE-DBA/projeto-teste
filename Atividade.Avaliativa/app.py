import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

def conectar():
    conn = sqlite3.connect("dados.db", timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabela_usuarios():
    sql = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        cpf TEXT,
        senha TEXT
    )
    """
    conn = conectar()
    conn.execute(sql)
    conn.commit()
    conn.close()

def atualizar_tabela_usuarios():
    conn = conectar()
    try:
        conn.execute("ALTER TABLE usuarios ADD COLUMN status TEXT DEFAULT 'Não entrou na fila'")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()

def criar_tabela_admin():
    sql = """
    CREATE TABLE IF NOT EXISTS administradores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        senha TEXT
    )
    """
    conn = conectar()
    conn.execute(sql)
    conn.commit()
    conn.close()

# Criar tabelas ao iniciar
criar_tabela_usuarios()
atualizar_tabela_usuarios()
criar_tabela_admin()

# ---------------- ROTAS USUÁRIO ----------------

@app.route("/")
def cadastro():
    return render_template("cadastro.html")

@app.route("/adicionar", methods=["POST"])
def adicionar():
    nome = request.form["nome"]
    email = request.form["email"]
    cpf = request.form["cpf"]
    senha = request.form["senha"]
    senha_hash = generate_password_hash(senha)

    conn = conectar()
    conn.execute("INSERT INTO usuarios (nome, email, cpf, senha, status) VALUES (?, ?, ?, ?, ?)",
                 (nome, email, cpf, senha_hash, "Não entrou na fila"))
    conn.commit()
    conn.close()
    return redirect(url_for("login"))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/entrar", methods=["POST"])
def entrar():
    email = request.form["email"]
    senha = request.form["senha"]
    conn = conectar()
    usuario = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    conn.close()
    if usuario and check_password_hash(usuario["senha"], senha):
        return redirect(url_for("dashboard", usuario_id=usuario["id"]))
    return "Email ou senha incorretos"

@app.route("/dashboard/<int:usuario_id>")
def dashboard(usuario_id):
    conn = conectar()
    usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    conn.close()
    return render_template("index_dashboard.html", usuario=usuario)

@app.route("/entrar_fila/<int:usuario_id>", methods=["POST"])
def entrar_fila(usuario_id):
    conn = conectar()
    conn.execute("UPDATE usuarios SET status = ? WHERE id = ?", ("Aguardando", usuario_id))
    conn.commit()
    conn.close()
    return redirect(url_for("fila", usuario_id=usuario_id))

@app.route("/fila/<int:usuario_id>")
def fila(usuario_id):
    conn = conectar()
    usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    conn.close()

    # Se a requisição vier com ?json=1, retorna apenas o status em JSON
    if request.args.get("json"):
        return jsonify({"status": usuario["status"]})

    return render_template("fila.html", usuario=usuario)

# Rota auxiliar para status em tempo real no dashboard
@app.route("/status/<int:usuario_id>")
def status(usuario_id):
    conn = conectar()
    usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    conn.close()
    return jsonify({"status": usuario["status"]})

@app.route("/atendimento")
def atendimento():
    conn = conectar()
    usuarios = conn.execute("SELECT * FROM usuarios").fetchall()
    conn.close()
    return render_template("index_atendimento.html", usuarios=usuarios)

# ---------------- ROTAS ADMIN ----------------

@app.route("/admin")
def admin_login():
    return render_template("admin_login.html")

@app.route("/cadastro_admin")
def cadastro_admin():
    return render_template("cadastrar_admin.html")

@app.route("/cadastrar_admin", methods=["POST"])
def cadastrar_admin():
    nome = request.form["nome"]
    email = request.form["email"]
    senha = request.form["senha"]
    senha_hash = generate_password_hash(senha)

    conn = conectar()
    conn.execute("INSERT INTO administradores (nome, email, senha) VALUES (?, ?, ?)",
                 (nome, email, senha_hash))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_login"))

@app.route("/entrar_admin", methods=["POST"])
def entrar_admin():
    email = request.form["email"]
    senha = request.form["senha"]
    conn = conectar()
    admin = conn.execute("SELECT * FROM administradores WHERE email = ?", (email,)).fetchone()
    conn.close()
    if admin and check_password_hash(admin["senha"], senha):
        conn = conectar()
        usuarios = conn.execute("SELECT * FROM usuarios").fetchall()
        conn.close()
        return render_template("admin_dashboard.html", usuarios=usuarios)
    return "Email ou senha incorretos (Admin)"

@app.route("/alterar_status/<int:usuario_id>", methods=["POST"])
def alterar_status(usuario_id):
    novo_status = request.form["status"]
    conn = conectar()
    conn.execute("UPDATE usuarios SET status = ? WHERE id = ?", (novo_status, usuario_id))
    conn.commit()
    conn.close()
    conn = conectar()
    usuarios = conn.execute("SELECT * FROM usuarios").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", usuarios=usuarios)

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
