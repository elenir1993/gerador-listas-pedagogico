import streamlit as st
import pdfplumber
import sqlite3
from fpdf import FPDF
from datetime import datetime

# --- CONEXÃO SEGURA COM O BANCO ---
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('escola_americo_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS turmas 
                 (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, ativa INTEGER, 
                  periodo TEXT, ultima_atualizacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS alunos 
                 (id INTEGER PRIMARY KEY, turma_id INTEGER, chamada TEXT, nome TEXT, 
                  FOREIGN KEY(turma_id) REFERENCES turmas(id))''')
    
    turmas_config = [
        ("1ª SÉRIE A MANHÃ", "Manhã"), ("1ª SÉRIE B MANHÃ", "Manhã"), ("1ª SÉRIE C MANHÃ", "Manhã"),
        ("2ª SÉRIE C MANHÃ", "Manhã"), ("2ª SÉRIE D MANHÃ", "Manhã"), ("2ª SÉRIE E MANHÃ", "Manhã"),
        ("2ª SÉRIE G MANHÃ", "Manhã"), ("3ª SÉRIE A MANHÃ", "Manhã"), ("3ª SÉRIE B MANHÃ", "Manhã"),
        ("3ª SÉRIE C MANHÃ", "Manhã"), ("3ª SÉRIE D MANHÃ", "Manhã"), ("3ª SÉRIE E MANHÃ", "Manhã"),
        ("3ª SÉRIE F MANHÃ", "Manhã"), ("1ª SÉRIE D NOITE", "Noite"), ("2ª SÉRIE F NOITE", "Noite"),
        ("2ª SÉRIE H NOITE", "Noite"), ("3ª SÉRIE J NOITE", "Noite"), ("3ª SÉRIE K NOITE", "Noite"),
        ("3ª SÉRIE L NOITE", "Noite"), ("1º TERMO A NOITE (EJA)", "EJA"), ("2º TERMO B NOITE (EJA)", "EJA"),
        ("3º TERMO B NOITE (EJA)", "EJA"), ("6º ANO A TARDE", "Tarde"), ("7º ANO A TARDE", "Tarde"),
        ("8º ANO A TARDE", "Tarde"), ("8º ANO B TARDE", "Tarde"), ("9º ANO A TARDE", "Tarde"),
        ("9º ANO B TARDE", "Tarde"), ("9º ANO C TARDE", "Tarde")
    ]
    for nome, periodo in turmas_config:
        c.execute("INSERT OR IGNORE INTO turmas (nome, ativa, periodo) VALUES (?, 0, ?)", (nome, periodo))
    conn.commit()
    return conn

conn = get_connection()

# --- PALETAS DE CORES ---
TEMAS = {
    "Azul Oficial": {"header": (44, 62, 80), "stripe": (245, 247, 249)},
    "Verde Pedagógico": {"header": (27, 94, 32), "stripe": (232, 245, 233)},
    "Vinho Clássico": {"header": (120, 0, 0), "stripe": (255, 245, 245)},
    "Grafite Moderno": {"header": (33, 33, 33), "stripe": (250, 250, 250)},
    "P&B (Econômico)": {"header": (0, 0, 0), "stripe": (255, 255, 255)}
}

# --- LÓGICA DE PDF ---
def extrair_alunos(nome_turma, arq_pdf):
    with pdfplumber.open(arq_pdf) as pdf:
        dados = []
        for pg in pdf.pages:
            tab = pg.extract_table()
            if tab:
                for lin in tab[1:]:
                    if lin and len(lin) > 6 and lin[0].isdigit() and lin[6] == "Ativo":
                        dados.append((lin[0], lin[1]))
    if dados:
        dt = datetime.now().strftime("%d/%m/%Y %H:%M")
        c = conn.cursor()
        c.execute("UPDATE turmas SET ultima_atualizacao = ? WHERE nome = ?", (dt, nome_turma))
        c.execute("SELECT id FROM turmas WHERE nome = ?", (nome_turma,))
        t_id = c.fetchone()[0]
        c.execute("DELETE FROM alunos WHERE turma_id = ?", (t_id,))
        c.executemany("INSERT INTO alunos (turma_id, chamada, nome) VALUES (?, ?, ?)", [(t_id, d[0], d[1]) for d in dados])
        conn.commit()
        return True
    return False

# --- UI STREAMLIT ---
st.set_page_config(page_title="Sistema Américo", layout="wide")
st.title("🏫 Gestão de Listas - EE Américo Brasiliense Doutor")

with st.sidebar:
    st.header("🎨 Estilo")
    tema_sel = st.selectbox("Cor do Tema", list(TEMAS.keys()))
    st.divider()
    finalidade = st.text_input("Finalidade da Lista", "Conselho de Classe")
    descricao = st.text_area("Descrição Opcional (sai no topo do PDF)")
    num_cols = st.slider("Assinaturas extras", 0, 3, 1)
    titulos = [st.text_input(f"Título Col {i+1}", "Assinatura") for i in range(num_cols)]

# SELEÇÃO EM MASSA (Corrigido para funcionar no clique)
st.subheader("⚡ Seleção Rápida por Turno")
bt1, bt2, bt3, bt4, bt5, bt6 = st.columns(6)
def mass_update(turno):
    conn.execute("UPDATE turmas SET ativa = 0")
    if turno != "Nenhum":
        conn.execute("UPDATE turmas SET ativa = 1 WHERE periodo = ?", (turno,))
    if turno == "Todos":
        conn.execute("UPDATE turmas SET ativa = 1")
    conn.commit()
    st.rerun()

if bt1.button("🌅 Manhã"): mass_update("Manhã")
if bt2.button("☀️ Tarde"): mass_update("Tarde")
if bt3.button("🌙 Noite"): mass_update("Noite")
if bt4.button("🎓 EJA"): mass_update("EJA")
if bt5.button("✅ Ativar Todas"): mass_update("Todos")
if bt6.button("❌ Limpar Seleção"): mass_update("Nenhum")

st.divider()

# QUADRO DE TURMAS
c = conn.cursor()
# Buscamos os dados SEMPRE após os botões para garantir atualização visual
c.execute("SELECT id, nome, ativa, ultima_atualizacao FROM turmas ORDER BY nome")
for t_id, t_nome, t_ativa, t_atu in c.fetchall():
    col_n, col_u, col_s = st.columns([4, 3, 1])
    with col_n:
        st.write(f"**{t_nome}**")
        # Mostra a data apenas se existir (elimina o 'None') 
        if t_atu:
            st.caption(f"🕒 Atualizado: {t_atu}")
        else:
            st.caption("⚠️ Aguardando PDF da SED")
    with col_u:
        f = st.file_uploader("Atualizar Alunos", type="pdf", key=f"up{t_id}", label_visibility="collapsed")
        if f and extrair_alunos(t_nome, f):
            st.rerun()
    with col_s:
        if st.toggle("Selecionado", value=bool(t_ativa), key=f"tg{t_id}") != bool(t_ativa):
            conn.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (1 if not t_ativa else 0, t_id))
            conn.commit()
            st.rerun()

# GERAÇÃO
if st.button("🚀 Gerar Listas em Massa", type="primary"):
    pdf = FPDF()
    c.execute("SELECT id, nome FROM turmas WHERE ativa = 1")
    ativas = c.fetchall()
    cores = TEMAS[tema_sel]
    
    if not ativas:
        st.warning("Selecione ao menos uma turma!")
    else:
        for t_id, t_nome in ativas:
            pdf.add_page()
            # Cabeçalho
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 8, 'EE AMÉRICO BRASILIENSE DOUTOR', 0, 1, 'C')
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, f"{finalidade.upper()} - {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'C')
            pdf.ln(2)
            
            # Info da Turma e Descrição
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(190, 8, f" TURMA: {t_nome}", 1, 1, 'L', True)
            if descricao:
                pdf.set_font('Arial', 'I', 8)
                pdf.multi_cell(190, 5, f"Descrição: {descricao}", 1, 'L')
            
            pdf.ln(2)

            # Tabela
            larg_n, larg_nome = 12, 85
            larg_ass = (190 - larg_n - larg_nome) / num_cols if num_cols > 0 else 0
            pdf.set_fill_color(*cores["header"])
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(larg_n, 8, "Nº", 1, 0, 'C', True)
            pdf.cell(larg_nome, 8, "NOME", 1, 0, 'C', True)
            for t in titulos: pdf.cell(larg_ass, 8, t.upper(), 1, 0, 'C', True)
            pdf.ln()

            c.execute("SELECT chamada, nome FROM alunos WHERE turma_id = ? ORDER BY CAST(chamada AS INTEGER)", (t_id,))
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 8)
            fill = False
            for ch, nm in c.fetchall():
                pdf.set_fill_color(*cores["stripe"]) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(larg_n, 5.5, ch, 1, 0, 'C', True)
                pdf.cell(larg_nome, 5.5, f" {nm[:42]}", 1, 0, 'L', True)
                for _ in range(num_cols): pdf.cell(larg_ass, 5.5, "", 1, 0, 'C', True)
                pdf.ln()
                fill = not fill
            
            # 5 Linhas Extras para novos alunos
            for _ in range(5):
                pdf.cell(larg_n, 5.5, "", 1, 0, 'C')
                pdf.cell(larg_nome, 5.5, " ____________________________________", 1, 0, 'L')
                for _ in range(num_cols): pdf.cell(larg_ass, 5.5, "", 1, 0)
                pdf.ln()

            # Observações no Rodapé
            pdf.ln(3)
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(0, 5, "OBSERVAÇÕES:", 0, 1, 'L')
            pdf.cell(190, 15, "", 1, 1, 'L')

        out = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Baixar PDF", out, f"Listas_{finalidade}.pdf")
