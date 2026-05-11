import streamlit as st
import pdfplumber
import sqlite3
from fpdf import FPDF
from datetime import datetime
import io

# --- BANCO DE DADOS (Conexão Única e Estável) ---
def get_db():
    conn = sqlite3.connect('americo_v7.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS turmas 
                 (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, ativa INTEGER, periodo TEXT, ultima_atu TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS alunos 
                 (id INTEGER PRIMARY KEY, turma_id INTEGER, chamada TEXT, nome TEXT)''')
    
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

db = get_db()

# --- TEMAS DE CORES ---
TEMAS = {
    "Azul Marinho": {"header": (44, 62, 80), "stripe": (245, 247, 249)},
    "Verde": {"header": (27, 94, 32), "stripe": (232, 245, 233)},
    "Vinho": {"header": (120, 0, 0), "stripe": (254, 245, 245)},
    "Grafite": {"header": (50, 50, 50), "stripe": (250, 250, 250)},
    "P&B": {"header": (0, 0, 0), "stripe": (255, 255, 255)}
}

# --- INTERFACE ---
st.set_page_config(page_title="Gestão Américo", layout="wide")
st.title("🏫 Sistema Pedagógico Otimizado - EE AMÉRICO BRASILIENSE DOUTOR")

with st.sidebar:
    st.header("🎨 Configuração")
    tema = st.selectbox("Cor do Tema", list(TEMAS.keys()))
    finalidade = st.text_input("Finalidade", "Lista de Presença")
    obs_extra = st.text_area("Descrição (Topo)")
    st.divider()
    num_col = st.slider("Colunas de Assinatura", 0, 5, 1)
    titulos = [st.text_input(f"Título Col {i+1}", f"Visto {i+1}", key=f"t{i}") for i in range(num_col)]
    
    if st.button("🚨 LIMPAR TODO O BANCO"):
        db.execute("DELETE FROM alunos")
        db.execute("UPDATE turmas SET ativa = 0, ultima_atu = NULL")
        db.commit()
        st.rerun()

# SELEÇÃO POR TURNO (Ação Instantânea)
st.subheader("⚡ Seleção Rápida")
c1, c2, c3, c4, c5 = st.columns(5)
def set_turno(p):
    db.execute("UPDATE turmas SET ativa = 0")
    if p != "OFF": db.execute("UPDATE turmas SET ativa = 1 WHERE periodo = ?", (p,))
    db.commit()
    st.rerun()

if c1.button("🌅 MANHÃ"): set_turno("MANHÃ")
if c2.button("☀️ TARDE"): set_turno("TARDE")
if c3.button("🌙 NOITE"): set_turno("NOITE")
if c4.button("🎓 EJA"): set_turno("EJA")
if c5.button("❌ DESATIVAR"): set_turno("OFF")

st.divider()

# QUADRO DE TURMAS
cursor = db.execute("SELECT id, nome, ativa, ultima_atu FROM turmas ORDER BY nome")
for t_id, t_nome, t_ativa, t_atu in cursor.fetchall():
    col_n, col_u, col_s = st.columns([4, 3, 1])
    with col_n:
        st.write(f"**{t_nome}**")
        st.caption(f"🕒 Atualizado: {t_atu}" if t_atu else "⚠️ Sem dados")
    
    with col_u:
        f = st.file_uploader("Subir PDF", type="pdf", key=f"up{t_id}", label_visibility="collapsed")
        if f:
            with pdfplumber.open(f) as pdf:
                db.execute("DELETE FROM alunos WHERE turma_id = ?", (t_id,))
                for pg in pdf.pages:
                    tab = pg.extract_table()
                    if tab:
                        for l in tab[1:]:
                            if l and len(l) > 6 and l[0].isdigit() and l[6] == "Ativo":
                                db.execute("INSERT INTO alunos (turma_id, chamada, nome) VALUES (?,?,?)", (t_id, l[0], l[1]))
            db.execute("UPDATE turmas SET ultima_atu = ? WHERE id = ?", (datetime.now().strftime("%d/%m/%Y %H:%M"), t_id))
            db.commit()
            st.rerun()

    with col_s:
        if st.toggle("Ativar", value=bool(t_ativa), key=f"tg{t_id}") != bool(t_ativa):
            db.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (1 if not t_ativa else 0, t_id))
            db.commit()
            st.rerun()

# --- GERAÇÃO RÁPIDA (Otimizada) ---
if st.button("🚀 GERAR DOCUMENTO (DOWNLOAD)", type="primary", use_container_width=True):
    ativas = db.execute("SELECT id, nome FROM turmas WHERE ativa = 1").fetchall()
    if not ativas:
        st.error("Selecione as turmas!")
    else:
        pdf = FPDF()
        cores = TEMAS[tema]
        
        for t_id, t_nome in ativas:
            pdf.add_page()
            # Cabeçalho
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'EE AMÉRICO BRASILIENSE DOUTOR', 0, 1, 'C')
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 5, f"{finalidade.upper()} - {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'C')
            pdf.ln(5)
            
            # Turma e Descrição
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(190, 10, f" TURMA: {t_nome}", 1, 1, 'L', True)
            if obs_extra:
                pdf.set_font('Arial', 'I', 9)
                pdf.multi_cell(190, 5, obs_extra, 1, 'L')
            pdf.ln(2)

            # Tabela
            larg_n, larg_nome = 12, 85
            larg_ass = (190 - larg_n - larg_nome) / num_col if num_col > 0 else 0
            pdf.set_fill_color(*cores["header"])
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(larg_n, 8, "Nº", 1, 0, 'C', True)
            pdf.cell(larg_nome, 8, "ALUNO", 1, 0, 'C', True)
            for t in titulos: pdf.cell(larg_ass, 8, t.upper(), 1, 0, 'C', True)
            pdf.ln()

            # Alunos
            alunos = db.execute("SELECT chamada, nome FROM alunos WHERE turma_id = ? ORDER BY CAST(chamada AS INTEGER)", (t_id,)).fetchall()
            pdf.set_text_color(0, 0, 0); pdf.set_font('Arial', '', 8)
            fill = False
            for ch, nm in alunos:
                pdf.set_fill_color(*cores["stripe"]) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(larg_n, 5.5, ch, 1, 0, 'C', True)
                pdf.cell(larg_nome, 5.5, f" {nm[:42]}", 1, 0, 'L', True)
                for _ in range(num_col): pdf.cell(larg_ass, 5.5, "", 1, 0, 'C', True)
                pdf.ln()
                fill = not fill
            
            # Linhas Extras e Obs
            for _ in range(5):
                pdf.cell(larg_n, 5.5, "", 1, 0, 'C')
                pdf.cell(larg_nome, 5.5, " ____________________________________", 1, 0, 'L')
                for _ in range(num_col): pdf.cell(larg_ass, 5.5, "", 1, 0)
                pdf.ln()
            
            pdf.ln(4); pdf.set_font('Arial', 'B', 8); pdf.cell(0, 5, "OBSERVAÇÕES:", 0, 1, 'L')
            pdf.cell(190, 15, "", 1, 1, 'L')

        # Download Imediato
        buffer = io.BytesIO()
        pdf_out = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 BAIXAR AGORA", pdf_out, f"Listas_{finalidade}.pdf", "application/pdf")
