from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date
import pymysql, hashlib, os
from ia import prever_espera

app = Flask(__name__)
app.secret_key = 'odontoflow-secret-2024'

# ── Configuração MySQL ─────────────────────────────────────────────────────────
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'odonto123',   # sua senha aqui
    'database': 'odontoflow',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# ── Procedimentos ──────────────────────────────────────────────────────────────
PROCEDIMENTOS = {
    'canal':    {'label': 'Canal',               'tempo': '90 - 120 min', 'minutos': 105},
    'aparelho': {'label': 'Manutencao Aparelho',  'tempo': '30 - 45 min',  'minutos': 37},
    'extracao': {'label': 'Extracao',             'tempo': '45 - 60 min',  'minutos': 52},
}

# ── Banco de dados ─────────────────────────────────────────────────────────────
def get_db():
    return pymysql.connect(**DB_CONFIG)

def init_db():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id      INT AUTO_INCREMENT PRIMARY KEY,
                nome    VARCHAR(150) NOT NULL,
                email   VARCHAR(150) NOT NULL UNIQUE,
                senha   VARCHAR(64)  NOT NULL,
                perfil  VARCHAR(20)  NOT NULL DEFAULT 'paciente'
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS agendamentos (
                id           INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id   INT          NOT NULL,
                procedimento VARCHAR(20)  NOT NULL,
                data         DATE         NOT NULL,
                hora         VARCHAR(5)   NOT NULL,
                obs          TEXT,
                status       VARCHAR(20)  NOT NULL DEFAULT 'aguardando',
                ticket       INT,
                criado_em    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        ''')
    conn.commit()
    conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# ── Helpers ────────────────────────────────────────────────────────────────────
def usuario_logado():
    return session.get('usuario_id') is not None

def enriquecer(row):
    proc = PROCEDIMENTOS.get(row['procedimento'], {})
    row['procedimento_label'] = proc.get('label', row['procedimento'])
    row['tempo_estimado']     = proc.get('tempo', '-')
    row['status_label'] = {
        'aguardando': 'Aguardando',
        'concluido':  'Concluido',
        'cancelado':  'Cancelado',
    }.get(row.get('status', ''), row.get('status', ''))
    return row

# ── Rotas ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if usuario_logado():
        return redirect(url_for('agendar'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if usuario_logado():
        return redirect(url_for('agendar'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM usuarios WHERE email=%s AND senha=%s',
                        (email, hash_senha(senha)))
            user = cur.fetchone()
        conn.close()
        if user:
            session['usuario_id']     = user['id']
            session['usuario_nome']   = user['nome']
            session['usuario_perfil'] = user['perfil']
            return redirect(url_for('agendar'))
        flash('E-mail ou senha incorretos.', 'erro')
    return render_template('login.html')


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if usuario_logado():
        return redirect(url_for('agendar'))
    if request.method == 'POST':
        nome  = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        if len(senha) < 6:
            flash('A senha precisa ter pelo menos 6 caracteres.', 'erro')
            return render_template('cadastro.html')
        try:
            conn = get_db()
            with conn.cursor() as cur:
                cur.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)',
                            (nome, email, hash_senha(senha)))
                conn.commit()
                cur.execute('SELECT * FROM usuarios WHERE email=%s', (email,))
                user = cur.fetchone()
            conn.close()
            session['usuario_id']     = user['id']
            session['usuario_nome']   = user['nome']
            session['usuario_perfil'] = user['perfil']
            flash('Conta criada! Agende sua consulta.', 'sucesso')
            return redirect(url_for('agendar'))
        except pymysql.err.IntegrityError:
            flash('Este e-mail ja esta cadastrado.', 'erro')
    return render_template('cadastro.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/agendar', methods=['GET', 'POST'])
def agendar():
    if not usuario_logado():
        return redirect(url_for('login'))
    if request.method == 'POST':
        procedimento = request.form.get('procedimento', '')
        data         = request.form.get('data', '')
        hora         = request.form.get('hora', '')
        obs          = request.form.get('obs', '').strip()
        if procedimento not in PROCEDIMENTOS:
            flash('Selecione um procedimento valido.', 'erro')
            return render_template('agendar.html', hoje=date.today().isoformat())
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) as total FROM agendamentos WHERE data=%s', (data,))
            ticket = cur.fetchone()['total'] + 1
            cur.execute('''INSERT INTO agendamentos
                           (usuario_id, procedimento, data, hora, obs, ticket)
                           VALUES (%s, %s, %s, %s, %s, %s)''',
                        (session['usuario_id'], procedimento, data, hora, obs, ticket))
        conn.commit()
        conn.close()
        proc = PROCEDIMENTOS[procedimento]
        pacientes_antes_count = ticket - 1
        minutos_ia, msg_ia = prever_espera(procedimento, data, hora, pacientes_antes_count)
        flash(f'Consulta agendada! Ticket #{ticket} · {proc["label"]} · {hora} — IA preve: {msg_ia}.', 'sucesso')
        return redirect(url_for('fila'))
    return render_template('agendar.html', hoje=date.today().isoformat())


@app.route('/fila')
def fila():
    if not usuario_logado():
        return redirect(url_for('login'))
    hoje = date.today().isoformat()
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute('''SELECT a.*, u.nome as nome_paciente
                       FROM agendamentos a JOIN usuarios u ON a.usuario_id=u.id
                       WHERE a.data=%s AND a.status='aguardando'
                       ORDER BY a.ticket''', (hoje,))
        rows = cur.fetchall()
    conn.close()

    fila_data = []
    meu_agendamento = None
    minutos_acumulados = 0

    for i, row in enumerate(rows):
        d = enriquecer(dict(row))
        eh_meu = (row['usuario_id'] == session['usuario_id'])
        d['meu'] = eh_meu
        partes = row['nome_paciente'].split()
        d['nome_exibido'] = f"{partes[0]} {partes[-1][0]}." if len(partes) >= 2 else partes[0]

        # IA prevê espera para cada paciente na fila
        minutos_ia, msg_ia = prever_espera(
            row['procedimento'], str(row['data']), row['hora'], i
        )
        d['previsao_ia'] = msg_ia

        fila_data.append(d)
        if eh_meu:
            horas = minutos_acumulados // 60
            mins  = minutos_acumulados % 60
            espera = f"{horas}h {mins:02d}min" if horas > 0 else (f"{mins} min" if mins > 0 else "Proximo!")
            meu_agendamento = {
                'ticket': row['ticket'],
                'procedimento_label': d['procedimento_label'],
                'data': str(row['data']),
                'hora': row['hora'],
                'posicao': i + 1,
                'espera_estimada': espera,
                'previsao_ia': msg_ia,
            }
        minutos_acumulados += PROCEDIMENTOS.get(row['procedimento'], {}).get('minutos', 0)

    return render_template('fila.html', fila=fila_data, meu_agendamento=meu_agendamento)


@app.route('/dashboard')
def dashboard():
    if not usuario_logado():
        return redirect(url_for('login'))
    hoje_iso = date.today().isoformat()
    hoje_fmt = date.today().strftime('%d/%m/%Y')
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute('''SELECT a.*, u.nome as nome_paciente
                       FROM agendamentos a JOIN usuarios u ON a.usuario_id=u.id
                       WHERE a.data=%s ORDER BY a.ticket''', (hoje_iso,))
        rows = cur.fetchall()
    conn.close()

    agendamentos = [enriquecer(dict(r)) for r in rows]
    stats = {
        'total':      len(agendamentos),
        'aguardando': sum(1 for a in agendamentos if a['status'] == 'aguardando'),
        'concluidos': sum(1 for a in agendamentos if a['status'] == 'concluido'),
        'tempo_medio': '-',
    }
    if stats['total'] > 0:
        media = sum(PROCEDIMENTOS.get(a['procedimento'], {}).get('minutos', 0) for a in agendamentos) // stats['total']
        stats['tempo_medio'] = f"{media} min"

    return render_template('dashboard.html', agendamentos=agendamentos, stats=stats, hoje=hoje_fmt)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
