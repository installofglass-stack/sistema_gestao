import pandas as pd
from sqlalchemy import create_engine

# URL externa correta do PostgreSQL no Render
DATABASE_URL = "postgresql://meu_estoque_user:efWAaNBCRkpM9SdTn2Xx2mHLm8kqej3m@dpg-da4ahum1egvs73blon7g-a.oregon-postgres.render.com/meu_estoque"

# Criando a conexão com o banco do Render
engine = create_engine(DATABASE_URL)

# Caminho para o seu arquivo CSV na pasta imports
arquivo_csv = "imports/view_acessorios.csv" 

print("Lendo a planilha CSV...")
df = pd.read_csv(arquivo_csv, encoding='utf-8', sep=None, engine='python')

print("Enviando os dados para o PostgreSQL no Render...")
df.to_sql('produtos', con=engine, if_exists='replace', index=False)

print("Pronto! Todos os dados foram importados com sucesso para a nuvem!")