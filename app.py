import streamlit as st
import pdfplumber
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# --- EXTRAÇÃO DE DADOS ---
def extrair_dados(arquivo_pdf):
    dados = []
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                # O PDF contém colunas de 0 a 6: Nº, Nome, RA, Dig, UF, Nasc, Situação 
                for linha in tabela[1:]:
                    # Filtra apenas quem é 'Ativo' 
                    if linha and len(linha) > 6 and linha[0] and linha[0].isdigit() and linha[6] == "Ativo":
                        dados.append([linha[0], linha[1]])
    return dados

# --- CLASSE PDF CUSTOMIZADA ---
class GeradorPDF(FPDF):
    def header(self):
        # Cabeçalho Institucional [cite: 1, 6, 10, 14]
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, 'SECRETARIA DA EDUCAÇÃO DO ESTADO DE SÃO PAULO', 0, 1, 'C')
        self.set_font('Arial', 'B', 12)
        self.cell(0, 7, 'EE AMÉRICO BRASILIENSE DOUTOR', 0, 1, 'C')
        self.ln(3)

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Gerador Américo", layout="centered")
st.title("📄 Gerador de Listas Profissional")

# Painel de Configurações
with st.expander("Configurações do Documento", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        turma = st.text_input("Série/Turma (Ex: 9º A)", "9º ANO A")
        finalidade = st.text_input("Finalidade", "Reunião de Pais")
    with col2:
        data_doc = st.date_input("Data", datetime.now())
        num_colunas = st.slider("Colunas de Registro", 1, 4, 1)

    titulos = []
    cols = st.columns(num_colunas)
    for i in range(num_colunas):
        titulos.append(cols[i].text_input(f"Título Col {i+1}", f"Assinatura"))

arquivo = st.file_uploader("Suba o arquivo da SED", type="pdf")

if arquivo:
    lista_alunos = extrair_dados(arquivo)
    st.info(f"Lista carregada com {len(lista_alunos)} alunos ativos.") [cite: 4, 8, 12, 16]

    if st.button("🚀 Gerar PDF de Página Única"):
        pdf = GeradorPDF()
        pdf.add_page()
        
        # Sub-cabeçalho com Turma e Detalhes
        pdf.set_fill_color(245, 245, 245)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(60, 8, f" TURMA: {turma.upper()}", 1, 0, 'L', True)
        pdf.cell(80, 8, f" FINALIDADE: {finalidade.upper()}", 1, 0, 'L', True)
        pdf.cell(50, 8, f" DATA: {data_doc.strftime('%d/%m/%Y')}", 1, 1, 'C', True)
        pdf.ln(2)

        # Cabeçalho da Tabela
        larg_n, larg_nome = 10, 75
        larg_extra = (190 - larg_n - larg_nome) / num_colunas
        
        pdf.set_fill_color(200, 200, 200)
        pdf.set_font('Arial', 'B', 8)
        pdf.cell(larg_n, 7, "Nº", 1, 0, 'C', True)
        pdf.cell(larg_nome, 7, "NOME DO ALUNO", 1, 0, 'C', True)
        for t in titulos:
            pdf.cell(larg_extra, 7, t.upper(), 1, 0, 'C', True)
        pdf.ln()

        # Lista de Alunos com Zebra-Stripe (visual mais bonito)
        pdf.set_font('Arial', '', 8)
        fill = False
        for aluno in lista_alunos:
            # Alterna cor de fundo para facilitar leitura
            pdf.set_fill_color(252, 252, 252) if not fill else pdf.set_fill_color(240, 240, 240)
            
            # Altura da linha reduzida (5.5) para caber em uma folha 
            pdf.cell(larg_n, 5.5, aluno[0], 1, 0, 'C', fill)
            pdf.cell(larg_nome, 5.5, f" {aluno[1][:40]}", 1, 0, 'L', fill)
            for _ in range(num_colunas):
                pdf.cell(larg_extra, 5.5, "", 1, 0, 'C', fill)
            pdf.ln()
            fill = not fill

        # Rodapé de Emissão [cite: 5, 9, 13, 17]
        pdf.ln(2)
        pdf.set_font('Arial', 'I', 7)
        pdf.cell(0, 5, f"Documento gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0, 'R')

        pdf_output = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Baixar Lista PDF", pdf_output, f"Lista_{turma}_{finalidade}.pdf")
