import sqlite3
import psycopg2

# 1. Conecta no banco antigo (SQLite local)
conn_sqlite = sqlite3.connect('data/meu_estoque.db')
cursor_sqlite = conn_sqlite.cursor()

# 2. Conecta no banco novo na nuvem (PostgreSQL do Render - URL Externa)
url_postgres = "postgresql://meu_estoque_user:efWAaNBCRkpM9SdTn2Xx2mHLm8kqej3m@dpg-da4ahum1egvs73blon7g-a.oregon-postgres.render.com/meu_estoque"
conn_pg = psycopg2.connect(url_postgres)
cursor_pg = conn_pg.cursor()

print("Conexões estabelecidas! Iniciando a migração...")

tabelas = ['acessorios', 'movimentacoes', 'precos_kg']

for tabela in tabelas:
    try:
        # Pega a instrução SQL exata que criou a tabela no SQLite
        cursor_sqlite.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{tabela}';")
        resultado = cursor_sqlite.fetchone()
        
        if not resultado or not resultado[0]:
            print(f"Tabela '{tabela}' não encontrada no SQLite.")
            continue
            
        sql_sqlite = resultado[0]
        
        # Converte o comando SQL do SQLite para um formato mais compatível com o PostgreSQL
        sql_postgres = sql_sqlite.replace("AUTOINCREMENT", "") \
                                 .replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY") \
                                 .replace("REAL", "DOUBLE PRECISION") \
                                 .replace("TEXT", "TEXT")
        
        print(f"Criando a tabela '{tabela}' no PostgreSQL...")
        cursor_pg.execute(f"DROP TABLE IF EXISTS {tabela} CASCADE;")
        cursor_pg.execute(sql_postgres)
        conn_pg.commit()
        
        # Agora busca os dados do SQLite
        cursor_sqlite.execute(f"SELECT * FROM {tabela}")
        linhas = cursor_sqlite.fetchall()
        
        if not linhas:
            print(f"A tabela '{tabela}' está vazia.")
            continue
            
        colunas = [description[0] for description in cursor_sqlite.description]
        colunas_str = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(colunas))
        
        print(f"Migrando {len(linhas)} registros da tabela '{tabela}'...")
        
        for linha in linhas:
            sql_insert = f"INSERT INTO {tabela} ({colunas_str}) VALUES ({placeholders})"
            try:
                cursor_pg.execute(sql_insert, linha)
            except Exception as err:
                conn_pg.rollback()
                print(falha := f"Erro na linha: {err}")
                
        conn_pg.commit()
        print(f"Tabela '{tabela}' migrada com sucesso!")
        
    except Exception as e:
        print(f"Erro ao processar a tabela {tabela}: {e}")
        conn_pg.rollback()

# Fecha as conexões
cursor_sqlite.close()
conn_sqlite.close()
cursor_pg.close()
conn_pg.close()

print("\nMigração finalizada! Todos os seus dados foram enviados para o Render com sucesso.")