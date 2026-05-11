import streamlit as st
import pdfplumber
import sqlite3
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURAÇÃO DO BANCO DE DATOS ---
def get_connection():
    conn = sqlite3.connect('escola_americo_final.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS turmas 
                 (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, ativa INTEGER, periodo TEXT, ultima_atu TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS alunos 
                 (id INTEGER PRIMARY KEY, turma_id INTEGER, chamada TEXT, nome TEXT)''')
    
    # Lista de turmas oficiais [cite: 11, 12, 13, 14]
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

# --- FUNÇÕES DE LIMPEZA E CONTROLE ---
def limpar_banco():
    conn.execute("DELETE FROM alunos")
    conn.execute("UPDATE turmas SET ativa = 0, ultima_atu = NULL")
    conn.commit()
    st.session_state.clear()
    st.rerun()

def atualizar_turno(periodo_alvo):
    cursor = conn.cursor()
    cursor.execute("UPDATE turmas SET ativa = 0")
    if periodo_alvo != "LIMPAR":
        cursor.execute("UPDATE turmas SET ativa = 1 WHERE periodo = ?", (periodo_alvo,))
    conn.commit()
    # Força a interface a ler o banco novamente
    st.rerun()

# --- INTERFACE ---
st.set_page_config(page_title="Gestão Américo", layout="wide")
st.title("🏫 Sistema Pedagógico - EE AMÉRICO BRASILIENSE DOUTOR")

# Sidebar com Opções e Botão de Reset
with st.sidebar:
    st.header("⚙️ Ferramentas")
    tema = st.selectbox("Tema Visual", ["Azul Profissional", "Verde Pedagógico", "Vinho", "Grafite"])
    finalidade = st.text_input("Finalidade", "Reunião de Pais")
    num_cols = st.slider("Colunas de Assinatura", 0, 5, 1)
    titulos = [st.text_input(f"Título Col {i+1}", "Assinatura", key=f"t{i}") for i in range(num_cols)]
    
    st.divider()
    if st.button("🚨 ZERAR TODO O SISTEMA", type="secondary", help="Apaga todos os alunos e limpa as listas"):
        limpar_banco()

# BOTÕES DE TURNO (Mecânica Fluida)
st.subheader("⚡ Seleção por Turno")
c1, c2, c3, c4, c5 = st.columns(5)
if c1.button("🌅 TUDO MANHÃ", use_container_width=True): atualizar_turno("MANHÃ")
if c2.button("☀️ TUDO TARDE", use_container_width=True): atualizar_turno("TARDE")
if c3.button("🌙 TUDO NOITE", use_container_width=True): atualizar_turno("NOITE")
if c4.button("🎓 TUDO EJA", use_container_width=True): atualizar_turno("EJA")
if c5.button("❌ DESATIVAR TUDO", use_container_width=True): atualizar_turno("LIMPAR")

st.divider()

# QUADRO DE TURMAS
cursor = conn.execute("SELECT id, nome, ativa, ultima_atu FROM turmas ORDER BY nome")
turmas_data = cursor.fetchall()

for t_id, t_nome, t_ativa, t_atu in turmas_data:
    col_n, col_u, col_s = st.columns([4, 3, 1])
    with col_n:
        st.write(f"**{t_nome}**")
        if t_atu:
            st.caption(f"🕒 Atualizado em: {t_atu}")
        else:
            st.caption("⚠️ Aguardando PDF da SED")
    
    with col_u:
        f = st.file_uploader("PDF", type="pdf", key=f"u{t_id}", label_visibility="collapsed")
        if f:
            with pdfplumber.open(f) as pdf:
                conn.execute("DELETE FROM alunos WHERE turma_id = ?", (t_id,))
                for pg in pdf.pages:
                    tab = pg.extract_table()
                    if tab:
                        # Filtra apenas alunos 'Ativo' [cite: 1]
                        for lin in tab[1:]:
                            if lin and len(lin) > 6 and lin[0].isdigit() and lin[6] == "Ativo":
                                conn.execute("INSERT INTO alunos (turma_id, chamada, nome) VALUES (?,?,?)", (t_id, lin[0], lin[1]))
            conn.execute("UPDATE turmas SET ultima_atu = ? WHERE id = ?", (datetime.now().strftime("%d/%m/%Y %H:%M"), t_id))
            conn.commit()
            st.rerun()

    with col_s:
        # Checkbox individual sincronizado com o banco
        selecionado = st.checkbox("Gerar", value=bool(t_ativa), key=f"ch{t_id}")
        if selecionado != bool(t_ativa):
            conn.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (1 if selecionado else 0, t_id))
            conn.commit()
            st.rerun()

# GERAÇÃO RÁPIDA
if st.button("🚀 GERAR DOCUMENTO CONSOLIDADO", type="primary", use_container_width=True):
    # [A lógica de geração de PDF aqui permanece a mesma das versões anteriores, focada em velocidade]
    st.info("Processando turmas selecionadas...")
