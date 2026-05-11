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
        self.set_text_color(60, 60, 60)
        self.cell(0, 5, 'SECRETARIA DA EDUCAÇÃO DO ESTADO DE SÃO PAULO', 0, 1, 'C')
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, 'ESCOLA ESTADUAL AMÉRICO BRASILIENSE DOUTOR', 0, 1, 'C')
        self.set_draw_color(150, 150, 150)
        self.line(10, 25, 200, 25)
        self.ln(6)

# --- INTERFACE ---
st.set_page_config(page_title="Sistema Américo", layout="wide")
st.title("🏫 Gestão de Turmas - Américo")

with st.sidebar:
    st.header("🎨 Layout da Lista")
    finalidade = st.text_input("Finalidade", "Reunião de Pais")
    data_doc = st.date_input("Data", datetime.now())
    st.divider()
    num_colunas = st.slider("Colunas de Assinatura", 0, 4, 1)
    titulos = [st.text_input(f"Título Coluna {i+1}", f"Assinatura", key=f"t{i}") for i in range(num_colunas)]
    obs_box = st.checkbox("Incluir campo de Observações no rodapé", value=True)

# Quadro de Turmas
st.subheader("Painel de Turmas")
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
        arq = st.file_uploader("Atualizar PDF", type="pdf", key=f"up_{t_id}", label_visibility="collapsed")
        if arq:
            if processar_pdf(t_nome, arq):
                st.success("Sincronizado!")
                st.rerun()
    with col_status:
        novo_status = st.toggle("Ativar", value=bool(t_ativa), key=f"tog_{t_id}")
        if novo_status != bool(t_ativa):
            c.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (int(novo_status), t_id))
            conn.commit()

st.divider()

if st.button("🚀 Gerar Listas", type="primary"):
    pdf = PDFEscolar()
    c.execute("SELECT id, nome FROM turmas WHERE ativa = 1")
    ativas = c.fetchall()
    
    if not ativas:
        st.warning("Selecione as turmas no quadro acima.")
    else:
        for t_id, t_nome in ativas:
            pdf.add_page()
            
            # Info da Turma
            pdf.set_fill_color(242, 244, 246)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(190, 10, f" TURMA: {t_nome}  |  FINALIDADE: {finalidade.upper()}  |  DATA: {data_doc.strftime('%d/%m/%Y')}", 1, 1, 'L', True)
            pdf.ln(2)

            # Cabeçalho da Tabela
            larg_n, larg_nome = 12, 85
            larg_restante = 190 - larg_n - larg_nome
            larg_ass = larg_restante / num_colunas if num_colunas > 0 else 0

            pdf.set_fill_color(44, 62, 80)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(larg_n, 8, "Nº", 1, 0, 'C', True)
            pdf.cell(larg_nome, 8, "NOME DO ALUNO", 1, 0, 'C', True)
            for t in titulos:
                pdf.cell(larg_ass, 8, t.upper(), 1, 0, 'C', True)
            pdf.ln()

            # Alunos
            c.execute("SELECT chamada, nome FROM alunos WHERE turma_id = ? ORDER BY CAST(chamada AS INTEGER)", (t_id,))
            alunos = c.fetchall()
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 8)
            fill = False
            
            for cham, nome in alunos:
                pdf.set_fill_color(255, 255, 255) if not fill else pdf.set_fill_color(248, 249, 250)
                pdf.cell(larg_n, 5.5, cham, 1, 0, 'C', True)
                pdf.cell(larg_nome, 5.5, f" {nome[:42]}", 1, 0, 'L', True)
                for _ in range(num_colunas):
                    pdf.cell(larg_ass, 5.5, "", 1, 0, 'C', True)
                pdf.ln()
                fill = not fill
            
            # Linhas extras para novos alunos
            pdf.set_fill_color(255, 255, 255)
            for _ in range(5):
                pdf.cell(larg_n, 5.5, "", 1, 0, 'C')
                pdf.cell(larg_nome, 5.5, " ____________________________________", 1, 0, 'L')
                for _ in range(num_colunas):
                    pdf.cell(larg_ass, 5.5, "", 1, 0)
                pdf.ln()

            # CAMPO DE OBSERVAÇÕES ABAIXO DA LISTA
            if obs_box:
                pdf.ln(4)
                pdf.set_font('Arial', 'B', 8)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5, "OBSERVAÇÕES:", 0, 1, 'L')
                pdf.set_draw_color(200, 200, 200)
                # Cria um quadro grande para anotações
                pdf.cell(190, 25, "", 1, 1, 'L')

        pdf_out = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Baixar Relatório", pdf_out, f"Relatorio_Americo_{finalidade}.pdf")
