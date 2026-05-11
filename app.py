import streamlit as st
import pdfplumber
import sqlite3
from fpdf import FPDF
from datetime import datetime
import io

# --- BANCO DE DATOS OTIMIZADO ---
def init_db():
    conn = sqlite3.connect('escola_americo_v6.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS turmas 
                 (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, ativa INTEGER, periodo TEXT, ultima_atu TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS alunos 
                 (id INTEGER PRIMARY KEY, turma_id INTEGER, chamada TEXT, nome TEXT)''')
    # Lista de turmas oficiais da unidade
    turmas_base = [
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
    for n, p in turmas_base:
        conn.execute("INSERT OR IGNORE INTO turmas (nome, ativa, periodo) VALUES (?, 0, ?)", (n, p))
    conn.commit()
    return conn

conn = init_db()

# --- TEMAS RÁPIDOS ---
TEMAS = {
    "Azul": {"header": (44, 62, 80), "stripe": (245, 247, 249)},
    "Verde": {"header": (27, 94, 32), "stripe": (232, 245, 233)},
    "Cinza": {"header": (60, 60, 60), "stripe": (250, 250, 250)}
}

# --- INTERFACE ---
st.set_page_config(page_title="Sistema Américo", layout="wide")
st.title("🚀 Gerador Veloz - EE Américo Brasiliense Doutor")

with st.sidebar:
    st.header("⚙️ Configuração")
    tema_sel = st.selectbox("Cor", list(TEMAS.keys()))
    finalidade = st.text_input("Finalidade", "Lista de Presença")
    num_cols = st.slider("Colunas Extras", 0, 5, 1)
    titulos = [st.text_input(f"Título {i+1}", "Assinatura", key=f"t{i}") for i in range(num_cols)]

# SELEÇÃO INSTANTÂNEA (Mecânica de Clique Fluida)
st.subheader("⚡ Seleção por Turno")
c1, c2, c3, c4 = st.columns(4)
if c1.button("🌅 MANHÃ"): conn.execute("UPDATE turmas SET ativa = (periodo='MANHÃ')"); conn.commit(); st.rerun()
if c2.button("☀️ TARDE"): conn.execute("UPDATE turmas SET ativa = (periodo='TARDE')"); conn.commit(); st.rerun()
if c3.button("🌙 NOITE"): conn.execute("UPDATE turmas SET ativa = (periodo='NOITE')"); conn.commit(); st.rerun()
if c4.button("❌ LIMPAR"): conn.execute("UPDATE turmas SET ativa = 0"); conn.commit(); st.rerun()

st.divider()

# QUADRO DE TURMAS
turmas_db = conn.execute("SELECT id, nome, ativa, ultima_atu FROM turmas ORDER BY nome").fetchall()
for t_id, t_nome, t_ativa, t_atu in turmas_db:
    col_n, col_u, col_s = st.columns([4, 3, 1])
    with col_n:
        st.write(f"**{t_nome}**")
        st.caption(f"🕒 {t_atu}" if t_atu else "⚠️ Sem dados")
    with col_u:
        f = st.file_uploader("PDF", type="pdf", key=f"u{t_id}", label_visibility="collapsed")
        if f:
            with pdfplumber.open(f) as pdf:
                conn.execute("DELETE FROM alunos WHERE turma_id = ?", (t_id,))
                for pg in pdf.pages:
                    tab = pg.extract_table()
                    if tab: # Filtro de alunos Ativos
                        for l in tab[1:]:
                            if l and len(l) > 6 and l[0].isdigit() and l[6] == "Ativo":
                                conn.execute("INSERT INTO alunos (turma_id, chamada, nome) VALUES (?,?,?)", (t_id, l[0], l[1]))
            conn.execute("UPDATE turmas SET ultima_atu = ? WHERE id = ?", (datetime.now().strftime("%d/%m/%Y %H:%M"), t_id))
            conn.commit()
            st.rerun()
    with col_s:
        if st.toggle("Ativo", value=bool(t_ativa), key=f"tg{t_id}") != bool(t_ativa):
            conn.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (1 if not t_ativa else 0, t_id))
            conn.commit()
            st.rerun()

# --- GERAÇÃO OTIMIZADA (Onde ganhamos velocidade) ---
if st.button("🚀 Gerar Tudo Agora", type="primary", use_container_width=True):
    ativas = conn.execute("SELECT id, nome FROM turmas WHERE ativa = 1").fetchall()
    if not ativas:
        st.warning("Selecione as turmas!")
    else:
        pdf = FPDF()
        cores = TEMAS[tema_sel]
        progresso = st.progress(0)
        
        for i, (t_id, t_nome) in enumerate(ativas):
            progresso.progress((i + 1) / len(ativas))
            pdf.add_page()
            # Cabeçalho Fixo
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'EE AMÉRICO BRASILIENSE DOUTOR', 0, 1, 'C')
            pdf.set_font('Arial', '', 9)
            pdf.cell(0, 5, f"{finalidade.upper()} | {t_nome}", 0, 1, 'C')
            pdf.ln(5)

            # Tabela
            larg_n, larg_nome = 12, 85
            larg_ass = (190 - larg_n - larg_nome) / num_cols if num_cols > 0 else 0
            pdf.set_fill_color(*cores["header"])
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(larg_n, 8, "Nº", 1, 0, 'C', True)
            pdf.cell(larg_nome, 8, "ALUNO", 1, 0, 'C', True)
            for t in titulos: pdf.cell(larg_ass, 8, t.upper(), 1, 0, 'C', True)
            pdf.ln()

            # Alunos (Busca única por página)
            alunos = conn.execute("SELECT chamada, nome FROM alunos WHERE turma_id = ? ORDER BY CAST(chamada AS INTEGER)", (t_id,)).fetchall()
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 8)
            fill = False
            for ch, nm in alunos:
                pdf.set_fill_color(*cores["stripe"]) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(larg_n, 5.5, ch, 1, 0, 'C', True)
                pdf.cell(larg_nome, 5.5, f" {nm[:42]}", 1, 0, 'L', True)
                for _ in range(num_cols): pdf.cell(larg_ass, 5.5, "", 1, 0, 'C', True)
                pdf.ln()
                fill = not fill
            
            # Linhas extras e Obs no Rodapé
            for _ in range(5):
                pdf.cell(larg_n, 5.5, "", 1, 0, 'C')
                pdf.cell(larg_nome, 5.5, " ____________________________________", 1, 0, 'L')
                for _ in range(num_cols): pdf.cell(larg_ass, 5.5, "", 1, 0)
                pdf.ln()
            
            pdf.ln(3); pdf.set_font('Arial', 'B', 8); pdf.cell(0, 5, "OBSERVAÇÕES:", 0, 1, 'L')
            pdf.cell(190, 15, "", 1, 1, 'L')

        out = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Baixar Agora", out, "Relatorio_Escolar.pdf")
        st.balloons()
