import streamlit as st
import pdfplumber
import sqlite3
from fpdf import FPDF
from datetime import datetime

# --- INICIALIZAÇÃO DO BANCO DE DATOS ---
def init_db():
    conn = sqlite3.connect('escola_americo.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS turmas 
                 (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, ativa INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS alunos 
                 (id INTEGER PRIMARY KEY, turma_id INTEGER, chamada TEXT, nome TEXT, 
                  FOREIGN KEY(turma_id) REFERENCES turmas(id))''')
    
    # Preenchimento automático das 29 turmas identificadas
    turmas_iniciais = [
        "1ª SÉRIE A MANHÃ", "1ª SÉRIE B MANHÃ", "1ª SÉRIE C MANHÃ", "1ª SÉRIE D NOITE",
        "2ª SÉRIE C MANHÃ", "2ª SÉRIE D MANHÃ", "2ª SÉRIE E MANHÃ", "2ª SÉRIE G MANHÃ",
        "2ª SÉRIE F NOITE", "2ª SÉRIE H NOITE", "3ª SÉRIE A MANHÃ", "3ª SÉRIE B MANHÃ",
        "3ª SÉRIE C MANHÃ", "3ª SÉRIE D MANHÃ", "3ª SÉRIE E MANHÃ", "3ª SÉRIE F MANHÃ",
        "3ª SÉRIE J NOITE", "3ª SÉRIE K NOITE", "3ª SÉRIE L NOITE", "1º TERMO A NOITE (EJA)",
        "2º TERMO B NOITE (EJA)", "3º TERMO B NOITE (EJA)", "6º ANO A TARDE", "7º ANO A TARDE",
        "8º ANO A TARDE", "8º ANO B TARDE", "9º ANO A TARDE", "9º ANO B TARDE", "9º ANO C TARDE"
    ]
    
    for t in turmas_iniciais:
        c.execute("INSERT OR IGNORE INTO turmas (nome, ativa) VALUES (?, 0)", (t,))
    
    conn.commit()
    return conn

conn = init_db()

# --- FUNÇÕES DE PROCESSAMENTO ---
def processar_pdf(nome_turma, arquivo_pdf):
    dados = []
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                for linha in tabela[1:]:
                    # Filtra apenas alunos 'Ativo' 
                    if linha and len(linha) > 6 and linha[0] and linha[0].isdigit() and linha[6] == "Ativo":
                        dados.append((linha[0], linha[1]))
    
    if dados:
        c = conn.cursor()
        c.execute("SELECT id FROM turmas WHERE nome = ?", (nome_turma,))
        t_id = c.fetchone()[0]
        c.execute("DELETE FROM alunos WHERE turma_id = ?", (t_id,))
        c.executemany("INSERT INTO alunos (turma_id, chamada, nome) VALUES (?, ?, ?)", 
                      [(t_id, d[0], d[1]) for d in dados])
        conn.commit()
        return True
    return False

class PDFEscolar(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, 'SECRETARIA DA EDUCAÇÃO DO ESTADO DE SÃO PAULO', 0, 1, 'C')
        self.set_font('Arial', 'B', 12)
        self.cell(0, 7, 'EE AMÉRICO BRASILIENSE DOUTOR', 0, 1, 'C')
        self.ln(5)

# --- INTERFACE ---
st.set_page_config(page_title="Sistema Américo", layout="wide")
st.title("🏫 Gestão de Turmas - Américo Brasiliense")

with st.sidebar:
    st.header("Configurações da Lista")
    finalidade = st.text_input("Finalidade", "Reunião de Pais")
    data_doc = st.date_input("Data", datetime.now())
    num_colunas = st.slider("Colunas de Registro", 1, 4, 1)
    titulos = [st.text_input(f"Título Col {i+1}", f"Assinatura", key=f"t{i}") for i in range(num_colunas)]

# Quadro de Turmas
st.subheader("Painel de Controle das Turmas")
st.info("Suba o PDF da SED uma única vez para salvar os alunos no sistema.")

c = conn.cursor()
c.execute("SELECT id, nome, ativa FROM turmas ORDER BY nome")
turmas_db = c.fetchall()

for t_id, t_nome, t_ativa in turmas_db:
    col_nome, col_upload, col_status = st.columns([3, 4, 1])
    
    with col_nome:
        st.write(f"**{t_nome}**")
        c.execute("SELECT COUNT(*) FROM alunos WHERE turma_id = ?", (t_id,))
        qtd = c.fetchone()[0]
        st.caption(f"{qtd} alunos ativos cadastrados")

    with col_upload:
        arq = st.file_uploader("Atualizar Alunos", type="pdf", key=f"up_{t_id}", label_visibility="collapsed")
        if arq:
            if processar_pdf(t_nome, arq):
                st.success("Dados Salvos!")
                st.rerun()

    with col_status:
        novo_status = st.toggle("Gerar", value=bool(t_ativa), key=f"tog_{t_id}")
        if novo_status != bool(t_ativa):
            c.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (int(novo_status), t_id))
            conn.commit()

# BOTÃO DE GERAÇÃO
st.divider()
if st.button("🚀 Gerar Listas (Página Única por Turma)", type="primary"):
    pdf = PDFEscolar()
    c.execute("SELECT id, nome FROM turmas WHERE ativa = 1")
    ativas = c.fetchall()
    
    if not ativas:
        st.warning("Selecione ao menos uma turma no botão 'Gerar' acima.")
    else:
        for t_id, t_nome in ativas:
            pdf.add_page()
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('Arial', 'B', 9)
            pdf.cell(60, 8, f" TURMA: {t_nome}", 1, 0, 'L', True)
            pdf.cell(80, 8, f" FINALIDADE: {finalidade.upper()}", 1, 0, 'L', True)
            pdf.cell(50, 8, f" DATA: {data_doc.strftime('%d/%m/%Y')}", 1, 1, 'C', True)
            pdf.ln(2)

            larg_n, larg_nome = 10, 75
            larg_extra = (190 - larg_n - larg_nome) / num_colunas
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(larg_n, 7, "Nº", 1, 0, 'C', True)
            pdf.cell(larg_nome, 7, "NOME DO ALUNO", 1, 0, 'C', True)
            for t in titulos: pdf.cell(larg_extra, 7, t.upper(), 1, 0, 'C', True)
            pdf.ln()

            c.execute("SELECT chamada, nome FROM alunos WHERE turma_id = ? ORDER BY CAST(chamada AS INTEGER)", (t_id,))
            alunos = c.fetchall()
            pdf.set_font('Arial', '', 8)
            fill = False
            for cham, nome in alunos:
                pdf.set_fill_color(252, 252, 252) if not fill else pdf.set_fill_color(240, 240, 240)
                pdf.cell(larg_n, 5.5, cham, 1, 0, 'C', True)
                pdf.cell(larg_nome, 5.5, f" {nome[:40]}", 1, 0, 'L', True)
                for _ in range(num_colunas): pdf.cell(larg_extra, 5.5, "", 1, 0, 'C', True)
                pdf.ln()
                fill = not fill
            
            # 5 LINHAS EXTRAS
            for i in range(5):
                pdf.set_fill_color(255, 255, 255)
                pdf.cell(larg_n, 5.5, "", 1, 0, 'C')
                pdf.cell(larg_nome, 5.5, " ________________________________", 1, 0, 'L')
                for _ in range(num_colunas): pdf.cell(larg_extra, 5.5, "", 1, 0)
                pdf.ln()

        pdf_out = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Baixar Arquivo Consolidado", pdf_out, f"Listas_{finalidade}.pdf")
