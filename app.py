from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date
import sqlite3, hashlib
from ia import prever_espera

app = Flask(__name__)
app.secret_key = 'odontoflow-secret-2024'

DB = "odontoflow.db"

PROCEDIMENTOS = {
    'canal':    {'label': 'Tratamento de Canal', 'tempo': '90 - 120 min', 'minutos': 105},
    'aparelho': {'label': 'Manutenção do Aparelho', 'tempo': '30 - 45 min', 'minutos': 37},
    'extracao': {'label': 'Extração de Dente', 'tempo': '45 - 60 min', 'minutos': 52},
}

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            perfil TEXT DEFAULT 'paciente'
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            procedimento TEXT,
            data TEXT,
            hora TEXT,
            obs TEXT,
            status TEXT DEFAULT 'aguardando',
            ticket INTEGER
        )
        """)

        conn.commit()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def logado():
    return 'usuario_id' in session

def enriquecer(row):
    p = PROCEDIMENTOS.get(row['procedimento'], {})
    row = dict(row)
    row['procedimento_label'] = p.get('label', row['procedimento'])
    row['tempo_estimado'] = p.get('tempo', '-')
    return row

@app.route('/')
def index():
    return redirect(url_for('agendar' if logado() else 'login'))

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if logado():
        return redirect(url_for('agendar'))

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        senha = hash_senha(request.form['senha'])

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM usuarios WHERE email=? AND senha=?", (email, senha))
            user = cur.fetchone()

        if user:
            session['usuario_id'] = user['id']
            session['nome'] = user['nome']
            return redirect(url_for('agendar'))

        flash("Login inválido")

    return render_template('login.html')

# ---------------- CADASTRO ----------------
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email'].strip().lower()
        senha = hash_senha(request.form['senha'])

        try:
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO usuarios (nome,email,senha) VALUES (?,?,?)",
                            (nome, email, senha))
                conn.commit()

            return redirect(url_for('login'))

        except sqlite3.IntegrityError:
            flash("Email já existe")

    return render_template('cadastro.html')

# ---------------- AGENDAR ----------------
@app.route('/agendar', methods=['GET', 'POST'])
def agendar():
    if not logado():
        return redirect(url_for('login'))

    if request.method == 'POST':
        proc = request.form['procedimento']
        data = request.form['data']
        hora = request.form['hora']
        obs = request.form.get('obs', '')  # <-- corrigido

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM agendamentos WHERE data=?", (data,))
            ticket = cur.fetchone()[0] + 1

            cur.execute("""
                INSERT INTO agendamentos (usuario_id, procedimento, data, hora, obs, ticket)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session['usuario_id'], proc, data, hora, obs, ticket))

            conn.commit()

        msg = prever_espera(proc, data, hora, ticket)
        flash(f"Agendado! #{ticket} - {msg}")

        return redirect(url_for('fila'))

    return render_template('agendar.html')

# ---------------- FILA ----------------
@app.route('/fila')
def fila():
    if not logado():
        return redirect(url_for('login'))

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.*, u.nome
            FROM agendamentos a
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.status='aguardando'
            ORDER BY a.data, a.ticket
        """)
        rows = cur.fetchall()

    fila = []
    for i, r in enumerate(rows):
        r = enriquecer(r)
        r = dict(r)
        r['posicao'] = i + 1
        fila.append(r)

    return render_template('fila.html', fila=fila)

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if not logado():
        return redirect(url_for('login'))

    hoje = date.today().isoformat()

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.*, u.nome as nome_paciente
            FROM agendamentos a
            JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.data=?
            ORDER BY a.hora
        """, (hoje,))
        rows = cur.fetchall()

    agendamentos = []
    for r in rows:
        r = enriquecer(r)
        r['status_label'] = (
            "Aguardando" if r['status'] == "aguardando"
            else "Concluído" if r['status'] == "concluido"
            else "Cancelado" if r['status'] == "cancelado"
            else r['status']
        )
        agendamentos.append(r)

    # estatísticas
    total = len(agendamentos)
    aguardando = sum(1 for r in agendamentos if r['status'] == 'aguardando')
    concluidos = sum(1 for r in agendamentos if r['status'] == 'concluido')
    tempos = [PROCEDIMENTOS.get(r['procedimento'], {}).get('minutos', 0) for r in agendamentos]
    tempo_medio = f"{round(sum(tempos)/len(tempos))} min" if tempos else "—"

    stats = {
        'total': total,
        'aguardando': aguardando,
        'concluidos': concluidos,
        'tempo_medio': tempo_medio
    }

    return render_template('dashboard.html', hoje=hoje, agendamentos=agendamentos, stats=stats)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()  # limpa todos os dados da sessão
    flash("Você saiu da conta")
    return redirect(url_for('login'))

# ---------------- START ----------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
