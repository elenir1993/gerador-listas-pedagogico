import streamlit as st
import pdfplumber
import sqlite3
from fpdf import FPDF
from datetime import datetime

# --- DATABASE & SESSION STATE ---
def get_connection():
    conn = sqlite3.connect('escola_americo_final.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS turmas 
                 (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, ativa INTEGER, periodo TEXT, ultima_atu TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS alunos 
                 (id INTEGER PRIMARY KEY, turma_id INTEGER, chamada TEXT, nome TEXT)''')
    
    # Lista de turmas da EE Américo Brasiliense Doutor
    turmas = [
        ("1ª SÉRIE A MANHÃ", "MANHÃ"), ("1ª SÉRIE B MANHÃ", "MANHÃ"), ("1ª SÉRIE C MANHÃ", "MANHÃ"),
        ("2ª SÉRIE C MANHÃ", "MANHÃ"), ("2ª SÉRIE D MANHÃ", "MANHÃ"), ("2ª SÉRIE E MANHÃ", "MANHÃ"),
        ("2ª SÉRIE G MANHÃ", "MANHÃ"), ("3ª SÉRIE A MANHÃ", "MANHÃ"), ("3ª SÉRIE B MANHÃ", "MANHÃ"),
        ("3ª SÉRIE C MANHÃ", "MANHÃ"), ("3ª SÉRIE D MANHÃ", "MANHÃ"), ("3ª SÉRIE E MANHÃ", "MANHÃ"),
        ("3ª SÉRIE F MANHÃ", "MANHÃ"), ("1ª SÉRIE D NOITE", "NOITE"), ("2ª SÉRIE F NOITE", "NOITE"),
        ("2ª SÉRIE H NOITE", "NOITE"), ("3ª SÉRIE J NOITE", "NOITE"), ("3ª SÉRIE K NOITE", "NOITE"),
        ("3ª SÉRIE L NOITE", "NOITE"), ("1º TERMO A NOITE (EJA)", "EJA"), ("2º TERMO B NOITE (EJA)", "EJA"),
        ("3º TERMO B NOITE (EJA)", "EJA"), ("6º ANO A TARDE", "TARDE"), ("7º ANO A TARDE", "TARDE"),
        ("8º ANO A TARDE", "TARDE"), ("8º ANO B TARDE", "TARDE"), ("9º ANO A TARDE", "TARDE"),
        ("9º ANO B TARDE", "TARDE"), ("9º ANO C TARDE", "TARDE")
    ]
    for n, p in turmas:
        conn.execute("INSERT OR IGNORE INTO turmas (nome, ativa, periodo) VALUES (?, 0, ?)", (n, p))
    conn.commit()
    return conn

conn = get_connection()

# Inicializa o estado das turmas se não existir
if 'selecionadas' not in st.session_state:
    cursor = conn.execute("SELECT id, ativa FROM turmas")
    st.session_state.selecionadas = {row[0]: bool(row[1]) for row in cursor.fetchall()}

# --- FUNÇÕES DE CALLBACK (A MÁGICA DA FLUIDEZ) ---
def mudar_turno(filtro):
    cursor = conn.cursor()
    if filtro == "LIMPAR":
        cursor.execute("UPDATE turmas SET ativa = 0")
    else:
        cursor.execute("UPDATE turmas SET ativa = 0")
        cursor.execute(f"UPDATE turmas SET ativa = 1 WHERE periodo = '{filtro}'")
    conn.commit()
    # Atualiza o Session State para refletir no UI imediatamente
    cursor.execute("SELECT id, ativa FROM turmas")
    st.session_state.selecionadas = {row[0]: bool(row[1]) for row in cursor.fetchall()}

def toggle_individual(t_id):
    nova_ativa = 1 if not st.session_state.selecionadas[t_id] else 0
    conn.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (nova_ativa, t_id))
    conn.commit()
    st.session_state.selecionadas[t_id] = bool(nova_ativa)

# --- TEMAS ---
TEMAS = {
    "Azul Américo": {"header": (44, 62, 80), "stripe": (245, 247, 249)},
    "Verde": {"header": (27, 94, 32), "stripe": (232, 245, 233)},
    "Vinho": {"header": (120, 0, 0), "stripe": (255, 245, 245)},
    "Cinza": {"header": (50, 50, 50), "stripe": (250, 250, 250)}
}

# --- UI ---
st.set_page_config(page_title="Sistema Américo", layout="wide")
st.title("🏫 Gestão de Listas - EE AMÉRICO BRASILIENSE DOUTOR")

with st.sidebar:
    tema = st.selectbox("Tema Visual", list(TEMAS.keys()))
    finalidade = st.text_input("Finalidade", "Reunião de Pais")
    desc = st.text_area("Descrição do Documento")
    n_col = st.slider("Colunas de Assinatura", 0, 3, 1)

# BOTÕES DE TURNO FLUIDOS
st.subheader("⚡ Seleção por Turno")
c1, c2, c3, c4, c5 = st.columns(5)
c1.button("🌅 Manhã", on_click=mudar_turno, args=("MANHÃ",), use_container_width=True)
c2.button("☀️ Tarde", on_click=mudar_turno, args=("TARDE",), use_container_width=True)
c3.button("🌙 Noite", on_click=mudar_turno, args=("NOITE",), use_container_width=True)
c4.button("🎓 EJA", on_click=mudar_turno, args=("EJA",), use_container_width=True)
c5.button("❌ Limpar Seleção", on_click=mudar_turno, args=("LIMPAR",), use_container_width=True)

st.divider()

# QUADRO DE TURMAS
cursor = conn.execute("SELECT id, nome, ultima_atu FROM turmas ORDER BY nome")
for t_id, t_nome, t_atu in cursor.fetchall():
    col_n, col_u, col_s = st.columns([3, 4, 1])
    with col_n:
        st.write(f"**{t_nome}**")
        st.caption(f"🕒 Atualizado: {t_atu}" if t_atu else "⚠️ Sem dados")
    with col_u:
        f = st.file_uploader("Subir PDF SED", type="pdf", key=f"u{t_id}", label_visibility="collapsed")
        if f:
            # Lógica de extração encurtada aqui...
            with pdfplumber.open(f) as pdf:
                # [Lógica para salvar alunos]
                pass
            dt = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.execute("UPDATE turmas SET ultima_atu = ? WHERE id = ?", (dt, t_id))
            conn.commit()
            st.rerun()
    with col_s:
        # Toggle conectado ao Session State
        st.toggle("Ativo", key=f"tog_{t_id}", 
                  value=st.session_state.selecionadas[t_id],
                  on_change=toggle_individual, args=(t_id,))

# GERAÇÃO DO PDF
if st.button("🚀 Gerar Listas Selecionadas", type="primary", use_container_width=True):
    # Lógica de geração do PDF com o tema escolhido e linhas extras...
    st.write("Gerando PDF...")
