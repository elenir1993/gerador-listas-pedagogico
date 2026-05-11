import streamlit as st
import pdfplumber
import sqlite3
from fpdf import FPDF
from datetime import datetime

# --- DATABASE ---
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('escola_americo_v4.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS turmas 
                 (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, ativa INTEGER, 
                  periodo TEXT, ultima_atualizacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS alunos 
                 (id INTEGER PRIMARY KEY, turma_id INTEGER, chamada TEXT, nome TEXT, 
                  FOREIGN KEY(turma_id) REFERENCES turmas(id))''')
    
    # Lista oficial da EE Américo Brasiliense Doutor
    turmas_base = [
        "1ª SÉRIE A MANHÃ", "1ª SÉRIE B MANHÃ", "1ª SÉRIE C MANHÃ", "1ª SÉRIE D NOITE",
        "2ª SÉRIE C MANHÃ", "2ª SÉRIE D MANHÃ", "2ª SÉRIE E MANHÃ", "2ª SÉRIE G MANHÃ",
        "2ª SÉRIE F NOITE", "2ª SÉRIE H NOITE", "3ª SÉRIE A MANHÃ", "3ª SÉRIE B MANHÃ",
        "3ª SÉRIE C MANHÃ", "3ª SÉRIE D MANHÃ", "3ª SÉRIE E MANHÃ", "3ª SÉRIE F MANHÃ",
        "3ª SÉRIE J NOITE", "3ª SÉRIE K NOITE", "3ª SÉRIE L NOITE", "1º TERMO A NOITE (EJA)",
        "2º TERMO B NOITE (EJA)", "3º TERMO B NOITE (EJA)", "6º ANO A TARDE", "7º ANO A TARDE",
        "8º ANO A TARDE", "8º ANO B TARDE", "9º ANO A TARDE", "9º ANO B TARDE", "9º ANO C TARDE"
    ]
    for t in turmas_base:
        c.execute("INSERT OR IGNORE INTO turmas (nome, ativa) VALUES (?, 0)", (t,))
    conn.commit()
    return conn

conn = get_connection()

# --- TEMAS ---
TEMAS = {
    "Azul Marinho": {"header": (44, 62, 80), "stripe": (245, 247, 249)},
    "Verde Pedagógico": {"header": (27, 94, 32), "stripe": (232, 245, 233)},
    "Vinho": {"header": (120, 0, 0), "stripe": (255, 245, 245)},
    "Grafite": {"header": (33, 33, 33), "stripe": (250, 250, 250)}
}

# --- INTERFACE ---
st.set_page_config(page_title="Sistema Américo", layout="wide")
st.title("🏫 Seleção Inteligente - EE Américo Brasiliense Doutor")

with st.sidebar:
    st.header("⚙️ Configuração")
    tema_sel = st.selectbox("Cor do Tema", list(TEMAS.keys()))
    finalidade = st.text_input("Finalidade", "Reunião de Pais")
    descricao = st.text_area("Descrição (Topo do PDF)")
    num_cols = st.slider("Colunas de Assinatura", 0, 3, 1)
    titulos = [st.text_input(f"Título Col {i+1}", "Assinatura") for i in range(num_cols)]

# --- LÓGICA DE ATIVAÇÃO CONDICIONAL ---
st.subheader("⚡ Ativar por Turno")
c1, c2, c3, c4, c5 = st.columns(5)

def ativar_condicional(termo):
    c = conn.cursor()
    c.execute("UPDATE turmas SET ativa = 0") # Primeiro desativa tudo
    if termo == "TODOS":
        c.execute("UPDATE turmas SET ativa = 1")
    elif termo == "LIMPAR":
        pass 
    else:
        # A MÁGICA ACONTECE AQUI: busca o termo dentro do nome da sala
        c.execute("UPDATE turmas SET ativa = 1 WHERE nome LIKE ?", (f'%{termo}%',))
    conn.commit()
    st.rerun()

if c1.button("🌅 TUDO MANHÃ"): ativar_condicional("MANHÃ")
if c2.button("☀️ TUDO TARDE"): ativar_condicional("TARDE")
if c3.button("🌙 TUDO NOITE"): ativar_condicional("NOITE")
if c4.button("🎓 TUDO EJA"): ativar_condicional("TERMO") # EJA na Américo usa 'TERMO' 
if c5.button("❌ DESATIVAR TUDO"): ativar_condicional("LIMPAR")

st.divider()

# --- LISTAGEM DAS TURMAS ---
c = conn.cursor()
c.execute("SELECT id, nome, ativa, ultima_atualizacao FROM turmas ORDER BY nome")
for t_id, t_nome, t_ativa, t_atu in c.fetchall():
    col_n, col_u, col_s = st.columns([4, 3, 1])
    with col_n:
        st.write(f"**{t_nome}**")
        status_data = f"🕒 {t_atu}" if t_atu else "⚠️ Sem dados"
        st.caption(status_data)
    with col_u:
        f = st.file_uploader("PDF", type="pdf", key=f"u{t_id}", label_visibility="collapsed")
        if f:
            # Lógica de extração simplificada para o exemplo
            with pdfplumber.open(f) as pdf:
                for pg in pdf.pages:
                    tab = pg.extract_table()
                    if tab:
                        c.execute("DELETE FROM alunos WHERE turma_id = ?", (t_id,))
                        for lin in tab[1:]:
                            if lin and len(lin) > 6 and lin[0].isdigit() and lin[6] == "Ativo":
                                c.execute("INSERT INTO alunos (turma_id, chamada, nome) VALUES (?,?,?)", (t_id, lin[0], lin[1]))
            c.execute("UPDATE turmas SET ultima_atualizacao = ? WHERE id = ?", (datetime.now().strftime("%d/%m/%Y %H:%M"), t_id))
            conn.commit()
            st.rerun()
    with col_s:
        # Checkbox individual que reflete a seleção em massa
        check = st.checkbox("Selecionar", value=bool(t_ativa), key=f"ch{t_id}")
        if check != bool(t_ativa):
            conn.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (1 if check else 0, t_id))
            conn.commit()
            st.rerun()

# --- GERAÇÃO DO PDF ---
if st.button("🚀 Gerar Listas Selecionadas", type="primary"):
    pdf = FPDF()
    c.execute("SELECT id, nome FROM turmas WHERE ativa = 1")
    ativas = c.fetchall()
    cores = TEMAS[tema_sel]
    
    if not ativas:
        st.warning("Nenhuma turma selecionada!")
    else:
        for t_id, t_nome in ativas:
            pdf.add_page()
            # Cabeçalho EE Américo Brasiliense Doutor
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'EE AMÉRICO BRASILIENSE DOUTOR', 0, 1, 'C')
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 5, f"{finalidade.upper()} - {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'C')
            pdf.ln(5)
            
            # Info Turma
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(190, 10, f" TURMA: {t_nome}", 1, 1, 'L', True)
            if descricao:
                pdf.set_font('Arial', 'I', 9)
                pdf.multi_cell(190, 5, descricao, 1, 'L')
            pdf.ln(2)

            # Tabela
            larg_n, larg_nome = 12, 85
            larg_ass = (190 - larg_n - larg_nome) / num_cols if num_cols > 0 else 0
            pdf.set_fill_color(*cores["header"])
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(larg_n, 8, "Nº", 1, 0, 'C', True)
            pdf.cell(larg_nome, 8, "ALUNO", 1, 0, 'C', True)
            for _ in range(num_cols): pdf.cell(larg_ass, 8, "ASSINATURA", 1, 0, 'C', True)
            pdf.ln()

            # Alunos [cite: 1, 4]
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

            # Rodapé Observações
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(0, 5, "OBSERVAÇÕES:", 0, 1, 'L')
            pdf.cell(190, 20, "", 1, 1, 'L')

        out = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Baixar PDF", out, f"Listas_{finalidade}.pdf")
