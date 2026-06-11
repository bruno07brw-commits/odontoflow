
# OdontoFlow

## Sobre o Projeto

O OdontoFlow é um sistema de gerenciamento odontológico desenvolvido para auxiliar clínicas na organização de consultas e atendimentos.

O sistema permite o cadastro de usuários, login, agendamento de consultas e organização dos atendimentos, proporcionando maior eficiência e melhor experiência para pacientes e profissionais.

---

## Motivação

O projeto foi criado com o objetivo de solucionar problemas comuns encontrados em clínicas odontológicas, como:

* Dificuldade na organização de horários;
* Filas de espera;
* Falta de previsão de atendimento;
* Controle manual de agendamentos.

---

## Tecnologias Utilizadas

* Python
* Flask
* SQLite
* HTML
* CSS
* JavaScript
* Git
* GitHub

---

## Funcionalidades

* Cadastro de usuários
* Sistema de login
* Agendamento de consultas
* Seleção de procedimentos odontológicos
* Estimativa de tempo de atendimento
* Organização dos atendimentos

---

## Estrutura do Projeto

```text
odontoflow/
│
├── app.py
├── requirements.txt
├── static/
├── templates/
├── database/
└── README.md
```

---

## Como Executar o Projeto

### 1. Clonar o Repositório

```bash
git clone https://github.com/bruno07brw-commits/odontoflow.git
```

### 2. Entrar na Pasta

```bash
cd odontoflow
```

### 3. Criar Ambiente Virtual

**Windows:**

```bash
python -m venv .odonto
.odonto\Scripts\activate
```

**Linux:**

```bash
python3 -m venv .odonto
source .odonto/bin/activate
```

### 4. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 5. Executar o Sistema

```bash
python app.py
```

---

## Banco de Dados

O OdontoFlow utiliza o **SQLite** para armazenar informações dos usuários, consultas e agendamentos.

### Visualização com DB Browser for SQLite

1. Instale o DB Browser for SQLite.
2. Abra o programa e clique em **Open Database**.
3. Selecione o arquivo do banco de dados do projeto (`database.db` ou `odontoflow.db`).
4. Utilize a aba **Browse Data** para visualizar as tabelas e os registros.

### Visualização pelo Terminal

Abrir o banco de dados:

```bash
sqlite3 database.db
```

ou

```bash
sqlite3 odontoflow.db
```

Listar tabelas:

```sql
.tables
```

Visualizar os dados de uma tabela:

```sql
SELECT * FROM nome_da_tabela;
```

Sair do SQLite:

```sql
.exit
```

---

## Equipe

* Bruno Henrique Alves dos Santos
* Bruno Augusto de Oliveira Perdomo
* Pedro Felipe Sampaio de Paula
* Geirryson Costa de Vieira

---

## Repositório

GitHub: https://github.com/bruno07brw-commits/odontoflow
