import streamlit as st
import pdfplumber
import sqlite3
from fpdf import FPDF
from datetime import datetime
import io

# --- BANCO DE DATOS (Conexão Única e Estável) ---
def get_db():
    # Versão 8 do banco para garantir integridade após as mudanças
    conn = sqlite3.connect('americo_v8.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS turmas 
                 (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, ativa INTEGER, ultima_atu TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS alunos 
                 (id INTEGER PRIMARY KEY, turma_id INTEGER, chamada TEXT, nome TEXT)''')
    
    # Lista de turmas oficiais da EE Américo Brasiliense Doutor
    turmas_base = [
        "1ª SÉRIE A MANHÃ", "1ª SÉRIE B MANHÃ", "1ª SÉRIE C MANHÃ", "1ª SÉRIE D NOITE",
        "2ª SÉRIE C MANHÃ", "2ª SÉRIE D MANHÃ", "2ª SÉRIE E MANHÃ", "2ª SÉRIE G MANHÃ",
        "2ª SÉRIE F NOITE", "2ª SÉRIE H NOITE", "3ª SÉRIE A MANHÃ", "3ª SÉRIE B MANHÃ",
        "3ª SÉRIE C MANHÃ", "3ª SÉRIE D MANHÃ", "3ª SÉRIE E MANHÃ", "3ª SÉRIE F MANHÃ",
        "3ª SÉRIE J NOITE", "3ª SÉRIE K NOITE", "3ª SÉRIE L NOITE", "1º TERMO A NOITE (EJA)",
        "2º TERMO B NOITE (EJA)", "3º TERMO B NOITE (EJA)", "6º ANO A TARDE", "7º ANO A TARDE",
        "8º ANO A TARDE", "8º ANO B TARDE", "9º ANO A TARDE", "9º ANO B TARDE", "9º ANO C TARDE"
    ]
    for n in turmas_base:
        conn.execute("INSERT OR IGNORE INTO turmas (nome, ativa) VALUES (?, 0)", (n,))
    conn.commit()
    return conn

db = get_db()

# --- TEMAS DE CORES ---
TEMAS = {
    "Azul Marinho": {"header": (44, 62, 80), "stripe": (245, 247, 249)},
    "Verde": {"header": (27, 94, 32), "stripe": (232, 245, 233)},
    "Cinza": {"header": (60, 60, 60), "stripe": (250, 250, 250)},
    "Vinho": {"header": (100, 14, 14), "stripe": (254, 245, 245)}
}

# --- INTERFACE ---
st.set_page_config(page_title="Gestão Américo", layout="wide")
st.title("🏫 Gestão Pedagógica - EE AMÉRICO BRASILIENSE DOUTOR")

with st.sidebar:
    st.header("🎨 Configurações da Lista")
    tema = st.selectbox("Cor do Tema", list(TEMAS.keys()))
    finalidade = st.text_input("Finalidade", "Lista de Presença")
    obs_extra = st.text_area("Descrição/Avisos (Topo)")
    st.divider()
    num_col = st.slider("Colunas de Assinatura", 0, 5, 1)
    titulos = [st.text_input(f"Título Col {i+1}", f"Coluna {i+1}", key=f"t{i}") for i in range(num_col)]
    
    st.divider()
    if st.button("🚨 LIMPAR TODO O BANCO", help="Apaga todos os alunos e limpa as datas"):
        db.execute("DELETE FROM alunos")
        db.execute("UPDATE turmas SET ativa = 0, ultima_atu = NULL")
        db.commit()
        st.rerun()

# --- QUADRO DE TURMAS (Seleção Individual) ---
st.subheader("📋 Quadro de Turmas")
st.info("Ative as turmas que deseja gerar e suba o PDF da SED para atualizar os alunos.")

cursor = db.execute("SELECT id, nome, ativa, ultima_atu FROM turmas ORDER BY nome")
for t_id, t_nome, t_ativa, t_atu in cursor.fetchall():
    col_n, col_u, col_s = st.columns([4, 3, 1])
    
    with col_n:
        st.write(f"**{t_nome}**")
        st.caption(f"🕒 Atualizado: {t_atu}" if t_atu else "⚠️ Sem dados cadastrados")
    
    with col_u:
        f = st.file_uploader("Upload PDF SED", type="pdf", key=f"up{t_id}", label_visibility="collapsed")
        if f:
            with pdfplumber.open(f) as pdf:
                db.execute("DELETE FROM alunos WHERE turma_id = ?", (t_id,))
                for pg in pdf.pages:
                    tab = pg.extract_table()
                    if tab: # Filtra apenas alunos ativos da Secretaria Escolar Digital
                        for l in tab[1:]:
                            if l and len(l) > 6 and l[0].isdigit() and l[6] == "Ativo":
                                db.execute("INSERT INTO alunos (turma_id, chamada, nome) VALUES (?,?,?)", (t_id, l[0], l[1]))
            db.execute("UPDATE turmas SET ultima_atu = ? WHERE id = ?", (datetime.now().strftime("%d/%m/%Y %H:%M"), t_id))
            db.commit()
            st.rerun()

    with col_s:
        # Checkbox individual fluida
        if st.toggle("Selecionar", value=bool(t_ativa), key=f"tg{t_id}") != bool(t_ativa):
            db.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (1 if not t_ativa else 0, t_id))
            db.commit()
            st.rerun()

# --- GERAÇÃO DO DOCUMENTO ---
st.divider()
if st.button("🚀 GERAR DOCUMENTO DAS TURMAS SELECIONADAS", type="primary", use_container_width=True):
    ativas = db.execute("SELECT id, nome FROM turmas WHERE ativa = 1").fetchall()
    if not ativas:
        st.error("Selecione ao menos uma turma no quadro acima!")
    else:
        pdf = FPDF()
        cores = TEMAS[tema]
        
        for t_id, t_nome in ativas:
            pdf.add_page()
            # Cabeçalho Oficial
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'ESCOLA ESTADUAL AMÉRICO BRASILIENSE DOUTOR', 0, 1, 'C')
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 5, f"{finalidade.upper()} - {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'C')
            pdf.ln(5)
            
            # Identificação da Turma
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(190, 10, f" TURMA: {t_nome}", 1, 1, 'L', True)
            if obs_extra:
                pdf.set_font('Arial', 'I', 9)
                pdf.multi_cell(190, 5, obs_extra, 1, 'L')
            pdf.ln(2)

            # Tabela de Chamada
            larg_n, larg_nome = 12, 85
            larg_ass = (190 - larg_n - larg_nome) / num_col if num_col > 0 else 0
            pdf.set_fill_color(*cores["header"])
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(larg_n, 8, "Nº", 1, 0, 'C', True)
            pdf.cell(larg_nome, 8, "NOME DO ALUNO", 1, 0, 'C', True)
            for t in titulos: pdf.cell(larg_ass, 8, t.upper(), 1, 0, 'C', True)
            pdf.ln()

            # Dados dos Alunos
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
            
            # Adição de 5 linhas extras para matrículas novas
            for _ in range(5):
                pdf.cell(larg_n, 5.5, "", 1, 0, 'C')
                pdf.cell(larg_nome, 5.5, " ____________________________________", 1, 0, 'L')
                for _ in range(num_colunas if 'num_colunas' in locals() else num_col): 
                    pdf.cell(larg_ass, 5.5, "", 1, 0)
                pdf.ln()
            
            # Campo de Observações Pedagógicas no Rodapé
            pdf.ln(4)
            pdf.set_font('Arial', 'B', 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, "OBSERVAÇÕES:", 0, 1, 'L')
            pdf.cell(190, 20, "", 1, 1, 'L')

        # Exportação do Arquivo
        pdf_out = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 BAIXAR DOCUMENTO CONSOLIDADO", pdf_out, f"Relatorio_Escolar_{finalidade}.pdf", "application/pdf")
