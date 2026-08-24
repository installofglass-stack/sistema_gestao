import os
import sqlite3

# Define o caminho do banco de dados na pasta data/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'data', 'meu_estoque.db')

def corrigir_texto(texto):
    if not isinstance(texto, str):
        return texto
    try:
        # Tenta reverter o erro de codificação UTF-8 misturado com Latin-1
        return texto.encode('latin1').decode('utf-8')
    except Exception:
        # Se falhar, retorna o texto original sem alterações
        return texto

def limpar_banco():
    if not os.path.exists(DB_NAME):
        print("Banco de dados não encontrado na pasta data/!")
        return

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Pega todos os registros da tabela acessorios
    cursor.execute("SELECT id, codigo, descricao, fornecedor, linha, cor, medida, sistema, observacao, material FROM acessorios")
    registros = cursor.fetchall()

    print(f"Analisando e corrigindo {len(registros)} registros...")

    for reg in registros:
        id_reg = reg['id']
        
        # Aplica a correção em cada campo de texto
        descricao = corrigir_texto(reg['descricao'])
        fornecedor = corrigir_texto(reg['fornecedor'])
        linha = corrigir_texto(reg['linha'])
        cor = corrigir_texto(reg['cor'])
        medida = corrigir_texto(reg['medida'])
        sistema = corrigir_texto(reg['sistema'])
        observacao = corrigir_texto(reg['observacao'])
        material = corrigir_texto(reg['material'])

        # Atualiza no banco de dados
        cursor.execute('''
            UPDATE acessorios 
            SET descricao=?, fornecedor=?, linha=?, cor=?, medida=?, sistema=?, observacao=?, material=?
            WHERE id=?
        ''', (descricao, fornecedor, linha, cor, medida, sistema, observacao, material, id_reg))

    conn.commit()
    conn.close()
    print("✨ Concluído! Todos os textos foram corrigidos com sucesso.")

if __name__ == '__main__':
    limpar_banco()