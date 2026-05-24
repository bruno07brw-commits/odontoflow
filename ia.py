import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import pickle
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'modelo_ia.pkl')

# ── Mapeamentos ────────────────────────────────────────────────────────────────
PROCEDIMENTOS_MAP = {'canal': 0, 'aparelho': 1, 'extracao': 2}
DIAS_MAP = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2,
            'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}

# ── Gerar dados simulados para treino ─────────────────────────────────────────
def gerar_dados_treino():
    np.random.seed(42)
    n = 2000

    procedimentos = np.random.choice(['canal', 'aparelho', 'extracao'], n)
    dias = np.random.choice(list(DIAS_MAP.keys()), n)
    horas = np.random.randint(8, 17, n)
    pacientes_antes = np.random.randint(0, 10, n)
    primeira_consulta = np.random.randint(0, 2, n)

    tempos_base = {'canal': 105, 'aparelho': 37, 'extracao': 52}
    tempo_real = []

    for i in range(n):
        base = tempos_base[procedimentos[i]]
        variacao = np.random.normal(0, 15)
        atraso_fila = pacientes_antes[i] * np.random.uniform(2, 8)
        extra_primeira = 10 if primeira_consulta[i] == 1 else 0
        extra_horario = 5 if horas[i] in [11, 16] else 0
        total = base + variacao + atraso_fila + extra_primeira + extra_horario
        tempo_real.append(max(10, total))

    df = pd.DataFrame({
        'procedimento': [PROCEDIMENTOS_MAP[p] for p in procedimentos],
        'dia_semana': [DIAS_MAP[d] for d in dias],
        'hora': horas,
        'pacientes_antes': pacientes_antes,
        'primeira_consulta': primeira_consulta,
        'tempo_real': tempo_real
    })

    return df

# ── Treinar e salvar modelo ────────────────────────────────────────────────────
def treinar_modelo():
    df = gerar_dados_treino()
    X = df[['procedimento', 'dia_semana', 'hora', 'pacientes_antes', 'primeira_consulta']]
    y = df['tempo_real']

    modelo = RandomForestRegressor(n_estimators=100, random_state=42)
    modelo.fit(X, y)

    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(modelo, f)

    print("Modelo treinado e salvo!")
    return modelo

# ── Carregar modelo ────────────────────────────────────────────────────────────
def carregar_modelo():
    if not os.path.exists(MODEL_PATH):
        return treinar_modelo()
    with open(MODEL_PATH, 'rb') as f:
        return pickle.load(f)

# ── Prever tempo de espera ─────────────────────────────────────────────────────
def prever_espera(procedimento, data_str, hora_str, pacientes_antes, primeira_consulta=False):
    """
    procedimento: 'canal', 'aparelho' ou 'extracao'
    data_str: '2026-05-24'
    hora_str: '14:00'
    pacientes_antes: int
    primeira_consulta: bool
    Retorna: (minutos_previstos, mensagem)
    """
    try:
        modelo = carregar_modelo()

        from datetime import datetime
        data = datetime.strptime(data_str, '%Y-%m-%d')
        dia_semana = DIAS_MAP[data.strftime('%A')]
        hora = int(hora_str.split(':')[0])
        proc = PROCEDIMENTOS_MAP.get(procedimento, 0)
        primeira = 1 if primeira_consulta else 0

        X = pd.DataFrame([[proc, dia_semana, hora, pacientes_antes, primeira]],
                         columns=['procedimento', 'dia_semana', 'hora',
                                  'pacientes_antes', 'primeira_consulta'])

        minutos = int(modelo.predict(X)[0])

        if minutos < 45:
            msg = f"Atendimento rapido — previsao de {minutos} min"
        elif minutos < 90:
            msg = f"Atendimento moderado — previsao de {minutos} min"
        else:
            msg = f"Atendimento longo — previsao de {minutos} min"

        return minutos, msg

    except Exception as e:
        return None, "Previsao indisponivel"


if __name__ == '__main__':
    treinar_modelo()
    minutos, msg = prever_espera('canal', '2026-05-26', '14:00', 3)
    print(f"Previsao: {minutos} min — {msg}")