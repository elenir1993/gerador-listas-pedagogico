import streamlit as st
import pdfplumber
import sqlite3
from fpdf import FPDF
from datetime import datetime

# --- INICIALIZAÇÃO DO BANCO COM AUTO-MIGRAÇÃO ---
def init_db():
    conn = sqlite3.connect('escola_americo.db', check_same_thread=False)
    c = conn.cursor()
    
    # Cria a tabela se não existir
    c.execute('''CREATE TABLE IF NOT EXISTS turmas 
                 (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, ativa INTEGER)''')
    
    # Verifica se as colunas novas existem (evita o erro da imagem)
    c.execute("PRAGMA table_info(turmas)")
    colunas_atuais = [coluna[1] for coluna in c.fetchall()]
    
    if 'periodo' not in colunas_atuais:
        c.execute("ALTER TABLE turmas ADD COLUMN periodo TEXT")
    if 'ultima_atualizacao' not in colunas_atuais:
        c.execute("ALTER TABLE turmas ADD COLUMN ultima_atualizacao TEXT")
        
    c.execute('''CREATE TABLE IF NOT EXISTS alunos 
                 (id INTEGER PRIMARY KEY, turma_id INTEGER, chamada TEXT, nome TEXT, 
                  FOREIGN KEY(turma_id) REFERENCES turmas(id))''')
    
    # Configuração das 29 turmas da EE Américo Brasiliense Doutor
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

conn = init_db()

# --- TEMAS DE CORES ---
TEMAS = {
    "Azul Marinho": {"header": (44, 62, 80), "stripe": (245, 247, 249)},
    "Verde Pedagógico": {"header": (30, 81, 40), "stripe": (240, 249, 242)},
    "Borgonha": {"header": (100, 14, 14), "stripe": (254, 245, 245)},
    "Cinza Profissional": {"header": (60, 60, 60), "stripe": (250, 250, 250)},
    "Minimalista (P&B)": {"header": (0, 0, 0), "stripe": (255, 255, 255)}
}

# --- PROCESSAMENTO ---
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
        data_atu = datetime.now().strftime("%d/%m/%Y %H:%M")
        c = conn.cursor()
        c.execute("UPDATE turmas SET ultima_atualizacao = ? WHERE nome = ?", (data_atu, nome_turma))
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
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'SECRETARIA DA EDUCAÇÃO DO ESTADO DE SÃO PAULO', 0, 1, 'C')
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, 'ESCOLA ESTADUAL AMÉRICO BRASILIENSE DOUTOR', 0, 1, 'C')
        self.line(10, 25, 200, 25)
        self.ln(6)

# --- INTERFACE ---
st.set_page_config(page_title="Gestão Américo", layout="wide")
st.title("🏫 Sistema Pedagógico - Américo Brasiliense")

with st.sidebar:
    st.header("🎨 Estilo e Conteúdo")
    tema = st.selectbox("Escolha a Cor da Lista", list(TEMAS.keys()))
    finalidade = st.text_input("Finalidade", "Reunião de Pais")
    descricao = st.text_area("Descrição Opcional", placeholder="Ex: Avisos sobre o conselho de classe...")
    st.divider()
    num_cols = st.slider("Colunas de Assinatura", 0, 4, 1)
    titulos_cols = [st.text_input(f"Título Col {i+1}", f"Visto", key=f"c{i}") for i in range(num_cols)]

# SELEÇÃO EM MASSA
st.subheader("⚡ Seleção por Turno")
c1, c2, c3, c4, c5 = st.columns(5)
turnos = [("Manhã", c1), ("Tarde", c2), ("Noite", c3), ("EJA", c4)]
for nome_t, col_t in turnos:
    if col_t.button(f"Ativar {nome_t}"):
        conn.execute("UPDATE turmas SET ativa = 0")
        conn.execute("UPDATE turmas SET ativa = 1 WHERE periodo = ?", (nome_t,))
        conn.commit()
        st.rerun()
if c5.button("Desativar Tudo"):
    conn.execute("UPDATE turmas SET ativa = 0")
    conn.commit()
    st.rerun()

st.divider()

# QUADRO DE TURMAS
c = conn.cursor()
c.execute("SELECT id, nome, ativa, ultima_atualizacao FROM turmas ORDER BY nome")
for t_id, t_nome, t_ativa, t_atu in c.fetchall():
    col_n, col_u, col_s = st.columns([3, 4, 1])
    with col_n:
        st.write(f"**{t_nome}**")
        # Remove o "None" e mostra a última atualização
        status_atu = t_atu if t_atu else "Nunca atualizado"
        st.caption(f"📅 {status_atu}")
    with col_u:
        f = st.file_uploader("PDF", type="pdf", key=f"up{t_id}", label_visibility="collapsed")
        if f and processar_pdf(t_nome, f):
            st.success("Salvo!")
            st.rerun()
    with col_s:
        if st.toggle("Ativo", value=bool(t_ativa), key=f"tg{t_id}") != bool(t_ativa):
            conn.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (1 if not t_ativa else 0, t_id))
            conn.commit()
            st.rerun()

# GERAÇÃO DO PDF
if st.button("🚀 Gerar Listas Selecionadas", type="primary"):
    pdf = PDFEscolar()
    c.execute("SELECT id, nome FROM turmas WHERE ativa = 1")
    ativas = c.fetchall()
    
    if not ativas:
        st.warning("Selecione ao menos uma turma.")
    else:
        cores = TEMAS[tema]
        for t_id, t_nome in ativas:
            pdf.add_page()
            # Info da Turma
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(190, 8, f" TURMA: {t_nome}  |  {finalidade.upper()}  |  DATA: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'L', True)
            
            if descricao:
                pdf.set_font('Arial', 'I', 8)
                pdf.multi_cell(190, 5, f"Observação: {descricao}", 0, 'L')
                pdf.ln(2)
            else: pdf.ln(3)

            # Tabela
            larg_n, larg_nome = 12, 85
            larg_ass = (190 - larg_n - larg_nome) / num_cols if num_cols > 0 else 0
            
            pdf.set_fill_color(*cores["header"])
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 8)
            pdf.cell(larg_n, 8, "Nº", 1, 0, 'C', True)
            pdf.cell(larg_nome, 8, "NOME DO ALUNO", 1, 0, 'C', True)
            for t in titulos_cols: pdf.cell(larg_ass, 8, t.upper(), 1, 0, 'C', True)
            pdf.ln()

            c.execute("SELECT chamada, nome FROM alunos WHERE turma_id = ? ORDER BY CAST(chamada AS INTEGER)", (t_id,))
            alunos = c.fetchall()
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Arial', '', 8)
            fill = False
            for cham, nome in alunos:
                pdf.set_fill_color(*cores["stripe"]) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(larg_n, 5.5, cham, 1, 0, 'C', True)
                pdf.cell(larg_nome, 5.5, f" {nome[:42]}", 1, 0, 'L', True)
                for _ in range(num_cols): pdf.cell(larg_ass, 5.5, "", 1, 0, 'C', True)
                pdf.ln()
                fill = not fill
            
            # Linhas extras e campo de observação
            for _ in range(5):
                pdf.cell(larg_n, 5.5, "", 1, 0, 'C')
                pdf.cell(larg_nome, 5.5, " ____________________________________", 1, 0, 'L')
                for _ in range(num_cols): pdf.cell(larg_ass, 5.5, "", 1, 0)
                pdf.ln()

            pdf.ln(4)
            pdf.set_font('Arial', 'B', 8)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, 5, "OBSERVAÇÕES DO PROFESSOR:", 0, 1, 'L')
            pdf.cell(190, 20, "", 1, 1, 'L')

        pdf_out = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Baixar PDF Consolidado", pdf_out, f"Listas_{finalidade}.pdf")
