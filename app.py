import streamlit as st
import pdfplumber
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# --- LÓGICA DE EXTRAÇÃO ---
def extrair_dados(arquivo_pdf):
    dados = []
    with pdfplumber.open(arquivo_pdf) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if tabela:
                # O PDF da SED possui colunas: Nº, Nome, RA, Dig, UF, Nasc, Situação 
                for linha in tabela[1:]:
                    if linha[0] and linha[0].isdigit() and linha[6] == "Ativo":
                        dados.append([linha[0], linha[1]]) # Nº e Nome [cite: 4]
    return dados

# --- CLASSE PARA O PDF FORMATADO ---
class GeradorPDF(FPDF):
    def header(self):
        # Cabeçalho Oficial extraído do documento padrão 
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, 'SECRETARIA DA EDUCAÇÃO DO ESTADO DE SÃO PAULO', 0, 1, 'C')
        self.set_font('Arial', 'B', 14)
        self.cell(0, 8, 'EE AMÉRICO BRASILIENSE DOUTOR', 0, 1, 'C')
        self.ln(10)

# --- INTERFACE DO USUÁRIO ---
st.title("🛠️ Central de Listas Américo")

# Configurações do Documento
col1, col2 = st.columns(2)
with col1:
    finalidade = st.text_input("Finalidade do Documento", "Reunião de Pais")
with col2:
    data_doc = st.date_input("Data", datetime.now())

# Configuração Dinâmica de Colunas
st.subheader("Configuração da Tabela")
num_colunas = st.number_input("Quantas colunas de registro (assinatura, livros, etc)?", 1, 5, 1)
titulos_colunas = []
cols = st.columns(num_colunas)
for i in range(num_colunas):
    titulos_colunas.append(cols[i].text_input(f"Título {i+1}", f"Coluna {i+1}"))

# Upload e Processamento
arquivo = st.file_uploader("Arraste o PDF da SED aqui", type="pdf")

if arquivo:
    lista_limpa = extrair_dados(arquivo)
    st.success(f"Sucesso! {len(lista_limpa)} alunos ATIVOS encontrados.")

    if st.button("Gerar Documento"):
        pdf = GeradorPDF()
        pdf.add_page()
        
        # Título da Atividade
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(100, 10, f"ATIVIDADE: {finalidade.upper()}", 0, 0)
        pdf.cell(90, 10, f"DATA: {data_doc.strftime('%d/%m/%Y')}", 0, 1, 'R')
        pdf.ln(5)

        # Cabeçalho da Tabela
        pdf.set_fill_color(240, 240, 240)
        larg_n, larg_nome = 12, 80
        larg_extra = (190 - larg_n - larg_nome) / num_colunas
        
        pdf.cell(larg_n, 10, "Nº", 1, 0, 'C', True)
        pdf.cell(larg_nome, 10, "NOME DO ALUNO", 1, 0, 'C', True)
        for t in titulos_colunas:
            pdf.cell(larg_extra, 10, t.upper(), 1, 0, 'C', True)
        pdf.ln()

        # Alunos
        pdf.set_font('Arial', '', 9)
        for aluno in lista_limpa:
            pdf.cell(larg_n, 8, aluno[0], 1, 0, 'C')
            pdf.cell(larg_nome, 8, aluno[1][:38], 1, 0, 'L')
            for _ in range(num_colunas):
                pdf.cell(larg_extra, 8, "", 1, 0)
            pdf.ln()

        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Baixar Lista Pronta", pdf_bytes, f"Lista_{finalidade}.pdf")
