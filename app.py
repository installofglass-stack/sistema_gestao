import os
import sqlite3
import pandas as pd
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, send_from_directory
from reportlab.lib.pagesizes import portrait, landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
EXPORTS_PDF_DIR = os.path.join(BASE_DIR, 'exports', 'pdf')
EXPORTS_EXCEL_DIR = os.path.join(BASE_DIR, 'exports', 'excel')
IMPORT_DIR = os.path.join(BASE_DIR, 'imports')

for folder in [DATA_DIR, UPLOAD_FOLDER, EXPORTS_PDF_DIR, EXPORTS_EXCEL_DIR, IMPORT_DIR]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DB_NAME = os.path.join(DATA_DIR, 'meu_estoque.db')

def fix_text(val):
    if not val or not isinstance(val, str): return val
    try:
        return val.encode('latin1').decode('utf-8')
    except:
        return val

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS acessorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imagem TEXT,
            codigo TEXT,
            descricao TEXT,
            fornecedor TEXT,
            linha TEXT,
            cor TEXT,
            medida TEXT,
            sistema TEXT,
            valor REAL,
            observacao TEXT,
            estoque INTEGER DEFAULT 0,
            nescessario INTEGER DEFAULT 0,
            material TEXT,
            peso_kg_m REAL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acessorio_id INTEGER,
            codigo TEXT,
            descricao TEXT,
            tipo TEXT,
            quantidade INTEGER,
            data TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS precos_kg (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cor TEXT UNIQUE,
            preco_kg REAL
        )
    ''')
    for col in [("estoque", "INTEGER DEFAULT 0"), ("nescessario", "INTEGER DEFAULT 0"), ("material", "TEXT"), ("peso_kg_m", "REAL DEFAULT 0")]:
        try:
            cursor.execute(f"ALTER TABLE acessorios ADD COLUMN {col[0]} {col[1]}")
        except:
            pass
    conn.commit()
    conn.close()

init_db()

def clean_num(val):
    try:
        if val is None or pd.isna(val): return 0.0
        s_str = str(val).strip().replace('R$', '').strip()
        if ',' in s_str and '.' in s_str:
            s_str = s_str.replace('.', '').replace(',', '.')
        elif ',' in s_str:
            s_str = s_str.replace(',', '.')
        return round(float(s_str), 3)
    except:
        return 0.0

def salvar_historico_arquivo():
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT * FROM movimentacoes", conn)
        conn.close()
        file_path = os.path.join(DATA_DIR, "historico_movimentacoes.csv")
        df.to_csv(file_path, index=False, sep=';', encoding='utf-8-sig')
    except Exception as e:
        print(f"Erro ao salvar arquivo de histórico: {e}")

def encontrar_imagem_na_pasta(codigo):
    if not codigo: return ""
    codigo_str = str(codigo).strip()
    if os.path.exists(UPLOAD_FOLDER):
        for arq in os.listdir(UPLOAD_FOLDER):
            if os.path.splitext(arq)[0].lower() == codigo_str.lower():
                return arq
    return ""

def get_most_used_values():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    data = {}
    for col in ['cor', 'fornecedor', 'medida', 'sistema', 'linha', 'material']:
        cursor.execute(f"SELECT DISTINCT TRIM({col}) FROM acessorios WHERE {col} IS NOT NULL AND TRIM({col}) != '' ORDER BY {col} ASC")
        data[col + 's'] = [fix_text(row[0]) for row in cursor.fetchall() if row[0]]
    
    cursor.execute("SELECT * FROM precos_kg ORDER BY cor ASC")
    precos_bruto = cursor.fetchall()
    data['precos_cores'] = [{'id': p['id'], 'cor': fix_text(p['cor']), 'preco_kg': p['preco_kg']} for p in precos_bruto]
    conn.close()
    return data

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM acessorios ORDER BY codigo ASC")
    registros_bruto = cursor.fetchall()
    
    registros = []
    for reg in registros_bruto:
        r_dict = dict(reg)
        for key in r_dict:
            if isinstance(r_dict[key], str):
                r_dict[key] = fix_text(r_dict[key])
        registros.append(r_dict)
    
    for reg in registros:
        if not reg['imagem'] and reg['codigo']:
            img = encontrar_imagem_na_pasta(reg['codigo'])
            if img:
                cursor.execute("UPDATE acessorios SET imagem = ? WHERE id = ?", (img, reg['id']))
                conn.commit()
                
    cursor.execute("SELECT COUNT(*), SUM(valor * COALESCE(estoque, 0)), COUNT(DISTINCT fornecedor) FROM acessorios")
    stats = cursor.fetchone()
    
    cursor.execute("SELECT * FROM precos_kg ORDER BY cor ASC")
    precos_cores = cursor.fetchall()
    
    conn.close()
    return render_template('index.html', 
                           registros=registros, 
                           total_itens=stats[0] or 0, 
                           soma_valor=stats[1] or 0.0, 
                           total_fornecedores=stats[2] or 0, 
                           dropdowns=get_most_used_values(), 
                           precos_cores=precos_cores, 
                           movimentacoes=[], 
                           abrir_modal_relatorio=False)

@app.route('/uploads/<path:filename>')
def servir_uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/salvar_preco_kg', methods=['POST'])
def salvar_preco_kg():
    cor = request.form.get('cor', '').strip().upper()
    preco_kg = clean_num(request.form.get('preco_kg'))
    if cor:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO precos_kg (cor, preco_kg) VALUES (?, ?)", (cor, preco_kg))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/excluir_preco_kg/<int:id>')
def excluir_preco_kg(id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM precos_kg WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/salvar', methods=['POST'])
def salvar():
    id_reg = request.form.get('id')
    codigo = request.form.get('codigo')
    descricao = request.form.get('descricao')
    fornecedor = request.form.get('fornecedor')
    linha = request.form.get('linha')
    cor = request.form.get('cor', '').strip().upper()
    medida = request.form.get('medida')
    sistema = request.form.get('sistema')
    observacao = request.form.get('observacao')
    estoque = int(clean_num(request.form.get('estoque')))
    nescessario = int(clean_num(request.form.get('nescessario')))
    material = request.form.get('material', '').strip().upper()
    peso_kg_m = clean_num(request.form.get('peso_kg_m'))
    valor = clean_num(request.form.get('valor'))
    
    if material == 'PERFIL' and peso_kg_m > 0 and cor:
        conn_temp = sqlite3.connect(DB_NAME)
        cur_temp = conn_temp.cursor()
        cur_temp.execute("SELECT preco_kg FROM precos_kg WHERE UPPER(cor) = UPPER(?)", (cor,))
        p_row = cur_temp.fetchone()
        conn_temp.close()
        if p_row:
            preco_kg = p_row[0]
            valor = preco_kg * peso_kg_m * 6.0

    img = encontrar_imagem_na_pasta(codigo)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if id_reg:
        cursor.execute('''
            UPDATE acessorios SET imagem=?, codigo=?, descricao=?, fornecedor=?, linha=?, cor=?, medida=?, sistema=?, valor=?, observacao=?, estoque=?, nescessario=?, material=?, peso_kg_m=? 
            WHERE id=?
        ''', (img, codigo, descricao, fornecedor, linha, cor, medida, sistema, valor, observacao, estoque, nescessario, material, peso_kg_m, id_reg))
    else:
        cursor.execute('''
            INSERT INTO acessorios (imagem, codigo, descricao, fornecedor, linha, cor, medida, sistema, valor, observacao, estoque, nescessario, material, peso_kg_m) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (img, codigo, descricao, fornecedor, linha, cor, medida, sistema, valor, observacao, estoque, nescessario, material, peso_kg_m))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/movimentar', methods=['POST'])
def movimentar():
    id_reg = request.form.get('id_mov')
    tipo = request.form.get('tipo_mov')
    qtd = int(clean_num(request.form.get('quantidade')))
    
    if qtd <= 0:
        return redirect(url_for('index'))
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, descricao, estoque, nescessario FROM acessorios WHERE id=?", (id_reg,))
    row = cursor.fetchone()
    
    if row:
        codigo, descricao, estoque, necessario = row[0], row[1], row[2], row[3]
        data_atual = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        if tipo == 'ENTRADA':
            novo_estoque = estoque + qtd
            cursor.execute("UPDATE acessorios SET estoque=? WHERE id=?", (novo_estoque, id_reg))
        elif tipo == 'SAIDA':
            novo_estoque = max(0, estoque - qtd)
            novo_necessario = max(0, necessario - qtd)
            cursor.execute("UPDATE acessorios SET estoque=?, nescessario=? WHERE id=?", (novo_estoque, novo_necessario, id_reg))
            
        cursor.execute('''
            INSERT INTO movimentacoes (acessorio_id, codigo, descricao, tipo, quantidade, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (id_reg, codigo, descricao, tipo, qtd, data_atual))
        
        conn.commit()
    conn.close()
    salvar_historico_arquivo()
    return redirect(url_for('index'))

@app.route('/excluir_movimento/<int:id>', methods=['POST'])
def excluir_movimento(id):
    nome = request.form.get('nome_autorizacao', '').strip()
    senha = request.form.get('senha_autorizacao', '').strip()
    
    if nome.lower() == "admin" and senha == "1234":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movimentacoes WHERE id=?", (id,))
        conn.commit()
        conn.close()
        salvar_historico_arquivo()
    
    return redirect(url_for('relatorio_movimentacoes'))

@app.route('/relatorio_movimentacoes')
def relatorio_movimentacoes():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM movimentacoes ORDER BY id DESC")
    movs = cursor.fetchall()
    
    cursor.execute("SELECT * FROM acessorios ORDER BY codigo ASC")
    registros = cursor.fetchall()
    cursor.execute("SELECT COUNT(*), SUM(valor * COALESCE(estoque, 0)), COUNT(DISTINCT fornecedor) FROM acessorios")
    stats = cursor.fetchone()
    
    cursor.execute("SELECT * FROM precos_kg ORDER BY cor ASC")
    precos_cores = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', 
                           registros=registros, 
                           total_itens=stats[0] or 0, 
                           soma_valor=stats[1] or 0.0, 
                           total_fornecedores=stats[2] or 0, 
                           dropdowns=get_most_used_values(),
                           precos_cores=precos_cores,
                           movimentacoes=movs,
                           abrir_modal_relatorio=True)

@app.route('/baixar_historico_arquivo')
def baixar_historico_arquivo():
    file_path = os.path.join(DATA_DIR, "historico_movimentacoes.csv")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return redirect(url_for('index'))

@app.route('/exportar_carrinho_pdf', methods=['POST'])
def exportar_carrinho_pdf():
    dados_json = request.form.get('carrinho_dados')
    if not dados_json: return redirect(url_for('index'))
    try: carrinho = json.loads(dados_json)
    except: return redirect(url_for('index'))
    if not carrinho: return redirect(url_for('index'))

    file_path = os.path.join(EXPORTS_PDF_DIR, "pedido_fornecedor.pdf")
    doc = SimpleDocTemplate(file_path, pagesize=portrait(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, leading=20, alignment=1, textColor=colors.HexColor('#212529'))
    style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9, leading=12, alignment=1)
    style_desc = ParagraphStyle('Desc', parent=styles['Normal'], fontSize=9, leading=12, alignment=0)
    style_header = ParagraphStyle('Header', parent=styles['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold', textColor=colors.whitesmoke, alignment=1)
    
    elements.append(Paragraph("<b>PEDIDO DE COMPRAS - FORNECEDOR</b>", style_title))
    elements.append(Spacer(1, 15))
    
    header_row = [Paragraph("Imagem", style_header), Paragraph("Código", style_header), Paragraph("Descrição", style_header), Paragraph("Cor", style_header), Paragraph("Quantidade", style_header)]
    data = [header_row]
    for item in carrinho:
        codigo = str(item.get('codigo', ''))
        img_element = Paragraph("Sem Foto", style_cell)
        img_nome = encontrar_imagem_na_pasta(codigo)
        if img_nome:
            img_path = os.path.join(UPLOAD_FOLDER, img_nome)
            if os.path.exists(img_path):
                try:
                    img_element = Image(img_path, width=35, height=25)
                    img_element.preserveAspectRatio = True
                    img_element.hAlign = 'CENTER'
                except: pass

        data.append([img_element, Paragraph(codigo, style_cell), Paragraph(str(item.get('descricao', '')), style_desc), Paragraph(str(item.get('cor', '')), style_cell), Paragraph(str(item.get('quantidade', 0)), style_cell)])
        
    t = Table(data, colWidths=[55, 70, 212, 100, 115])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#343a40')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t)
    doc.build(elements)
    return send_file(file_path, as_attachment=True)

@app.route('/duplicar/<int:id>')
def duplicar(id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT imagem, codigo, descricao, fornecedor, linha, cor, medida, sistema, valor, observacao, estoque, nescessario, material, peso_kg_m FROM acessorios WHERE id=?", (id,))
    row = cursor.fetchone()
    if row:
        novo_codigo = str(row[1]) + "_copia"
        img = encontrar_imagem_na_pasta(novo_codigo) or row[0]
        cursor.execute('''
            INSERT INTO acessorios (imagem, codigo, descricao, fornecedor, linha, cor, medida, sistema, valor, observacao, estoque, nescessario, material, peso_kg_m) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (img, novo_codigo, row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13]))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/excluir/<int:id>')
def excluir(id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM acessorios WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/importar_excel', methods=['POST'])
def importar_excel():
    file = request.files.get('excel_file')
    if file:
        file_path = os.path.join(IMPORT_DIR, file.filename)
        file.save(file_path)
        try:
            if file.filename.endswith('.csv'):
                try: df = pd.read_csv(file_path, sep=';', encoding='utf-8-sig')
                except: df = pd.read_csv(file_path, sep=',', encoding='utf-8-sig')
            else: df = pd.read_excel(file_path)
            
            df.columns = [str(c).lower().strip() for c in df.columns]
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                codigo = str(row.get('codigo', '')).strip()
                if not codigo or codigo.lower() == 'nan': continue
                
                descricao = str(row.get('descricao', ''))
                fornecedor = str(row.get('fornecedor', ''))
                linha = str(row.get('linha', ''))
                cor = str(row.get('cor', '')).strip().upper()
                medida = str(row.get('medida', ''))
                sistema = str(row.get('sistema', ''))
                observacao = str(row.get('observacao', ''))
                material = str(row.get('material', '')).strip().upper()
                img_csv = str(row.get('imagem', row.get('image', ''))).strip()
                
                estoque = int(clean_num(row.get('estoque', 0)))
                nescessario = int(clean_num(row.get('nescessario', 0)))
                peso_kg_m = clean_num(row.get('peso_kg_m', 0))
                valor = clean_num(row.get('valor', 0))

                if material == 'PERFIL' and peso_kg_m > 0 and cor:
                    cursor.execute("SELECT preco_kg FROM precos_kg WHERE UPPER(cor) = UPPER(?)", (cor,))
                    p_row = cursor.fetchone()
                    if p_row: valor = p_row[0] * peso_kg_m * 6.0
                
                img_final = encontrar_imagem_na_pasta(codigo)
                if not img_final and img_csv and img_csv.lower() != 'nan': img_final = img_csv

                cursor.execute("SELECT id FROM acessorios WHERE codigo = ?", (codigo,))
                existe = cursor.fetchone()
                
                if existe:
                    cursor.execute('''
                        UPDATE acessorios SET imagem=?, descricao=?, fornecedor=?, linha=?, cor=?, medida=?, sistema=?, valor=?, observacao=?, estoque=?, nescessario=?, material=?, peso_kg_m=? 
                        WHERE id=?
                    ''', (img_final, descricao, fornecedor, linha, cor, medida, sistema, valor, observacao, estoque, nescessario, material, peso_kg_m, existe[0]))
                else:
                    cursor.execute('''
                        INSERT INTO acessorios (imagem, codigo, descricao, fornecedor, linha, cor, medida, sistema, valor, observacao, estoque, nescessario, material, peso_kg_m) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ''', (img_final, codigo, descricao, fornecedor, linha, cor, medida, sistema, valor, observacao, estoque, nescessario, material, peso_kg_m))
            conn.commit()
            conn.close()
        except Exception as e: print(f"Erro na importação: {e}")
    return redirect(url_for('index'))

@app.route('/exportar_excel')
def exportar_excel():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM acessorios", conn)
    conn.close()
    file_path = os.path.join(EXPORTS_EXCEL_DIR, "relatorio.xlsx")
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

@app.route('/exportar_csv')
def exportar_csv():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM acessorios", conn)
    conn.close()
    file_path = os.path.join(EXPORTS_EXCEL_DIR, "relatorio.csv")
    df.to_csv(file_path, index=False, sep=';', encoding='utf-8-sig')
    return send_file(file_path, as_attachment=True)

@app.route('/exportar_pdf', methods=['POST'])
def exportar_pdf():
    ids_json = request.form.get('ids_filtrados')
    ids_filtrados = json.loads(ids_json) if ids_json else []

    colunas_selecionadas = request.form.getlist('colunas')
    if not colunas_selecionadas:
        colunas_selecionadas = ['codigo', 'descricao', 'cor', 'fornecedor', 'medida', 'sistema', 'linha', 'observacao', 'valor', 'material', 'peso_kg_m']

    orientacao = request.form.get('orientacao', 'paisagem')
    page_size = portrait(letter) if orientacao == 'retrato' else landscape(letter)
    usable_width = 552 if orientacao == 'retrato' else 732

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if ids_filtrados:
        placeholders = ','.join(['?'] * len(ids_filtrados))
        query = f"SELECT imagem, codigo, descricao, fornecedor, linha, cor, medida, sistema, valor, observacao, material, peso_kg_m FROM acessorios WHERE id IN ({placeholders})"
        cursor.execute(query, ids_filtrados)
    else:
        cursor.execute("SELECT imagem, codigo, descricao, fornecedor, linha, cor, medida, sistema, valor, observacao, material, peso_kg_m FROM acessorios")
        
    rows = cursor.fetchall()
    conn.close()

    file_path = os.path.join(EXPORTS_PDF_DIR, "relatorio_acessorios.pdf")
    doc = SimpleDocTemplate(file_path, pagesize=page_size, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, leading=10, alignment=1)
    style_desc = ParagraphStyle('Desc', parent=styles['Normal'], fontSize=8, leading=10, alignment=0)
    style_header = ParagraphStyle('Header', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold', textColor=colors.whitesmoke, alignment=1)
    
    base_widths = {'imagem': 55, 'codigo': 70, 'descricao': 130, 'cor': 60, 'fornecedor': 70, 'medida': 50, 'sistema': 60, 'linha': 60, 'observacao': 80, 'valor': 60, 'material': 60, 'peso_kg_m': 60}
    col_map = {'imagem': (0, 'Imagem'), 'codigo': (1, 'Código'), 'descricao': (2, 'Descrição'), 'fornecedor': (3, 'Fornecedor'), 'linha': (4, 'Linha'), 'cor': (5, 'Cor'), 'medida': (6, 'Medida'), 'sistema': (7, 'Sistema'), 'valor': (8, 'Valor'), 'observacao': (9, 'Observação'), 'material': (10, 'Material'), 'peso_kg_m': (11, 'Kg/m')}
    
    valid_cols = [c for c in colunas_selecionadas if c in col_map]
    total_base = sum(base_widths.get(c, 70) for c in valid_cols)
    scale = usable_width / total_base if total_base > 0 else 1
    
    header_row = [Paragraph(col_map[c][1], style_header) for c in valid_cols]
    col_widths = [base_widths.get(c, 70) * scale for c in valid_cols]
        
    data = [header_row]
    for row in rows:
        row_data = []
        for c in valid_cols:
            idx = col_map[c][0]
            if idx == 0:
                img_nome = row[0]
                img_element = Paragraph("Sem Foto", style_cell)
                if img_nome:
                    img_path = os.path.join(UPLOAD_FOLDER, img_nome)
                    if os.path.exists(img_path):
                        try:
                            img_element = Image(img_path, width=35, height=25)
                            img_element.preserveAspectRatio = True
                            img_element.hAlign = 'CENTER'
                        except: pass
                row_data.append(img_element)
            elif idx == 8:
                val = row[8]
                row_data.append(Paragraph(f"R$ {val:.2f}" if val is not None else "R$ 0.00", style_cell))
            elif idx == 11:
                p_m = row[11]
                row_data.append(Paragraph(f"{p_m:.3f}" if p_m else "0.000", style_cell))
            else:
                txt = fix_text(str(row[idx] if row[idx] is not None and str(row[idx]).lower() != 'none' else ""))
                sty = style_desc if c in ['descricao', 'observacao'] else style_cell
                row_data.append(Paragraph(txt, sty))
        data.append(row_data)
        
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#343a40')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t)
    doc.build(elements)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)