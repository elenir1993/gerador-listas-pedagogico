import streamlit as st
import pdfplumber
import sqlite3
from fpdf import FPDF
from datetime import datetime
import io

# --- BANCO DE DADOS ---
def get_db():
    conn = sqlite3.connect('americo_v10.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS turmas 
                 (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, ativa INTEGER DEFAULT 0, ultima_atu TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS alunos 
                 (id INTEGER PRIMARY KEY, turma_id INTEGER, chamada TEXT, nome TEXT)''')
    turmas_base = [
        "1ª SÉRIE A MANHÃ", "1ª SÉRIE B MANHÃ", "1ª SÉRIE C MANHÃ", "1ª SÉRIE D NOITE",
        "2ª SÉRIE C MANHÃ", "2ª SÉRIE D MANHÃ", "2ª SÉRIE E MANHÃ", "2ª SÉRIE G MANHÃ",
        "2ª SÉRIE F NOITE", "2ª SÉRIE H NOITE",
        "3ª SÉRIE A MANHÃ", "3ª SÉRIE B MANHÃ", "3ª SÉRIE C MANHÃ", "3ª SÉRIE D MANHÃ",
        "3ª SÉRIE E MANHÃ", "3ª SÉRIE F MANHÃ", "3ª SÉRIE J NOITE", "3ª SÉRIE K NOITE", "3ª SÉRIE L NOITE",
        "2ª SÉRIE A MANHÃ (ADMINISTRAÇÃO)", "2ª SÉRIE B MANHÃ (DESENV. SISTEMAS)", 
        "3ª SÉRIE G MANHÃ (DESENV. SISTEMAS)", "3ª SÉRIE H MANHÃ (SEG. TRABALHO)",
        "1º TERMO A NOITE (EJA)", "2º TERMO B NOITE (EJA)", "3º TERMO B NOITE (EJA)",
        "6º ANO A TARDE", "7º ANO A TARDE", "8º ANO A TARDE", "8º ANO B TARDE",
        "9º ANO A TARDE", "9º ANO B TARDE", "9º ANO C TARDE"
    ]
    for n in turmas_base:
        conn.execute("INSERT OR IGNORE INTO turmas (nome, ativa) VALUES (?, 0)", (n,))
    conn.commit()
    return conn

@st.cache_resource
def get_cached_db():
    return get_db()

db = get_cached_db()

# --- TEMAS DE CORES ---
TEMAS = {
    "Azul Marinho": {"header": (44, 62, 80), "stripe": (245, 247, 249)},
    "Verde Pedagógico": {"header": (27, 94, 32), "stripe": (232, 245, 233)},
    "Vinho Elegante": {"header": (100, 14, 14), "stripe": (254, 245, 245)},
    "Cinza Profissional": {"header": (60, 60, 60), "stripe": (250, 250, 250)},
    "Econômico (P&B)": {"header": (0, 0, 0), "stripe": (255, 255, 255)}
}

# --- PROCESSAMENTO DO PDF ---
def processar_pdf(pdf_bytes, turma_id):
    """
    Extrai alunos com situação 'Ativo' do PDF da SED.
    Vincula ao turma_id recebido como parâmetro — não depende de leitura de nome no PDF.
    """
    alunos_inseridos = 0
    try:
        db.execute("DELETE FROM alunos WHERE turma_id = ?", (turma_id,))
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for pg in pdf.pages:
                tab = pg.extract_table()
                if not tab:
                    continue
                for linha in tab[1:]:
                    if not linha or len(linha) < 7:
                        continue
                    chamada  = (linha[0] or "").strip()
                    nome     = (linha[1] or "").strip()
                    # Pega a última célula não-vazia como situação
                    situacao = next(
                        (str(c).strip().upper() for c in reversed(linha) if c and str(c).strip()),
                        ""
                    )
                    if chamada.isdigit() and nome and situacao == "ATIVO":
                        db.execute(
                            "INSERT INTO alunos (turma_id, chamada, nome) VALUES (?,?,?)",
                            (turma_id, chamada, nome)
                        )
                        alunos_inseridos += 1
        db.execute(
            "UPDATE turmas SET ultima_atu = ? WHERE id = ?",
            (datetime.now().strftime("%d/%m/%Y %H:%M"), turma_id)
        )
        db.commit()
        return alunos_inseridos, None
    except Exception as e:
        return 0, str(e)

# --- GERAÇÃO DO PDF ---
def gerar_pdf(turmas_ativas, finalidade, data_documento, obs_extra, tema, num_col, titulos_cols):
    cores = TEMAS[tema]
    pdf = FPDF()

    for t_id, t_nome in turmas_ativas:
        alunos = db.execute(
            "SELECT chamada, nome FROM alunos WHERE turma_id = ? ORDER BY CAST(chamada AS INTEGER)",
            (t_id,)
        ).fetchall()

        pdf.add_page()

        # Cabeçalho institucional
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "ESCOLA ESTADUAL DOUTOR AMÉRICO BRASILIENSE", 0, 1, "C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, f"{finalidade.upper()} — {data_documento.strftime('%d/%m/%Y')}", 0, 1, "C")
        pdf.ln(4)

        # Faixa com nome da turma
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(190, 10, f"  TURMA: {t_nome}", 1, 1, "L", True)

        if obs_extra:
            pdf.set_font("Arial", "I", 9)
            pdf.multi_cell(190, 5, obs_extra, 1, "L")
        pdf.ln(2)

        # Dimensões da tabela
        larg_n    = 12
        larg_nome = 85
        colunas   = titulos_cols if num_col > 0 else [""]
        larg_col  = (190 - larg_n - larg_nome) / len(colunas)

        # Cabeçalho da tabela
        pdf.set_fill_color(*cores["header"])
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(larg_n,    8, "Nº",            1, 0, "C", True)
        pdf.cell(larg_nome, 8, "NOME DO ALUNO", 1, 0, "C", True)
        for tc in colunas:
            pdf.cell(larg_col, 8, tc.upper()[:20], 1, 0, "C", True)
        pdf.ln()

        # Linhas de alunos
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 8)
        fill = False
        for ch, nm in alunos:
            pdf.set_fill_color(*(cores["stripe"] if fill else (255, 255, 255)))
            pdf.cell(larg_n,    5.5, str(ch),        1, 0, "C", True)
            pdf.cell(larg_nome, 5.5, f" {nm[:42]}",  1, 0, "L", True)
            for _ in colunas:
                pdf.cell(larg_col, 5.5, "", 1, 0, "C", True)
            pdf.ln()
            fill = not fill

        # 5 linhas em branco para novas matrículas
        pdf.set_fill_color(255, 255, 255)
        for _ in range(5):
            pdf.cell(larg_n,    5.5, "", 1, 0, "C")
            pdf.cell(larg_nome, 5.5, " ____________________________________", 1, 0, "L")
            for _ in colunas:
                pdf.cell(larg_col, 5.5, "", 1, 0)
            pdf.ln()

        # Rodapé
        pdf.ln(2)
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 5, f"Total de alunos ativos: {len(alunos)}", 0, 1, "R")
        pdf.ln(2)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 5, "OBSERVAÇÕES:", 0, 1, "L")
        pdf.cell(190, 20, "", 1, 1, "L")

    return pdf.output(dest="S").encode("latin-1")

# =====================================================================
# INTERFACE PRINCIPAL
# =====================================================================
st.set_page_config(page_title="Gestão Américo", layout="wide")
st.title("🏫 Sistema de Gestão de Listas — EE Dr. Américo Brasiliense")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📅 Configurações do Documento")
    data_documento = st.date_input("Data da lista", datetime.now())
    finalidade     = st.text_input("Finalidade", "Lista de Presença")
    tema           = st.selectbox("Cor do Tema", list(TEMAS.keys()))
    obs_extra      = st.text_area("Descrição/Avisos (aparece no topo do PDF)")

    st.divider()
    st.subheader("Colunas Extras")
    num_col = st.slider("Quantidade de colunas extras", 0, 5, 1)
    titulos_cols = [
        st.text_input(f"Título da Coluna {i+1}", f"Visto {i+1}", key=f"t{i}")
        for i in range(num_col)
    ]

    st.divider()
    if st.button("🚨 LIMPAR TODO O BANCO", help="Apaga todos os alunos e limpa os dados salvos"):
        db.execute("DELETE FROM alunos")
        db.execute("UPDATE turmas SET ativa = 0, ultima_atu = NULL")
        db.commit()
        st.success("Banco limpo com sucesso!")
        st.rerun()

# --- PAINEL DE TURMAS ---
st.subheader("📋 Painel de Controle de Turmas")

turmas = db.execute(
    "SELECT id, nome, ativa, ultima_atu FROM turmas ORDER BY nome"
).fetchall()

for t_id, t_nome, t_ativa, t_atu in turmas:
    col_n, col_u, col_s = st.columns([4, 3, 1])

    with col_n:
        qtd = db.execute(
            "SELECT COUNT(*) FROM alunos WHERE turma_id = ?", (t_id,)
        ).fetchone()[0]
        st.write(f"**{t_nome}**")
        if t_atu:
            st.caption(f"🕒 {t_atu} — {qtd} aluno(s) ativo(s)")
        else:
            st.caption("⚠️ Sem dados importados")

    with col_u:
        arquivo = st.file_uploader(
            "Upload PDF SED",
            type="pdf",
            key=f"up_{t_id}",        # ← key única e estável por turma (correção principal)
            label_visibility="collapsed"
        )
        if arquivo is not None:
            pdf_bytes = arquivo.read()   # lê os bytes antes de fechar o buffer
            inseridos, erro = processar_pdf(pdf_bytes, t_id)
            if erro:
                st.error(f"Erro ao processar PDF: {erro}")
            else:
                st.success(f"✅ {inseridos} aluno(s) importado(s) para {t_nome}")
                st.rerun()

    with col_s:
        novo_valor = st.toggle("Selecionar", value=bool(t_ativa), key=f"tg_{t_id}")
        if novo_valor != bool(t_ativa):
            db.execute("UPDATE turmas SET ativa = ? WHERE id = ?", (1 if novo_valor else 0, t_id))
            db.commit()
            st.rerun()

# --- GERAÇÃO DO PDF ---
st.divider()

turmas_ativas = db.execute(
    "SELECT id, nome FROM turmas WHERE ativa = 1 ORDER BY nome"
).fetchall()

col_info, col_btn = st.columns([3, 1])
with col_info:
    if turmas_ativas:
        nomes = ", ".join(n for _, n in turmas_ativas)
        st.info(f"**{len(turmas_ativas)} turma(s) selecionada(s):** {nomes}")
    else:
        st.warning("Selecione ao menos uma turma para gerar o documento.")

with col_btn:
    gerar = st.button(
        "🚀 GERAR DOCUMENTO",
        type="primary",
        use_container_width=True,
        disabled=(len(turmas_ativas) == 0)
    )

if gerar:
    with st.spinner("Gerando PDF..."):
        pdf_bytes = gerar_pdf(
            turmas_ativas, finalidade, data_documento,
            obs_extra, tema, num_col, titulos_cols
        )
    nome_arquivo = f"Listas_{finalidade.replace(' ', '_')}_{data_documento.strftime('%d-%m-%Y')}.pdf"
    st.download_button(
        "📥 BAIXAR RELATÓRIO",
        data=pdf_bytes,
        file_name=nome_arquivo,
        mime="application/pdf"
    )
    st.success(f"✅ Documento gerado com {len(turmas_ativas)} turma(s)!")
