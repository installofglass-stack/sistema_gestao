import sqlite3

# Nome do seu novo arquivo de banco de dados
DB_NAME = 'meu_estoque.db'

def criar_banco():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Criando a tabela exatamente com as colunas que você usa
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
            observacao TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Banco de dados '{DB_NAME}' criado com sucesso!")

if __name__ == '__main__':
    criar_banco()