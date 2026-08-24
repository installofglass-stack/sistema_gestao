@echo off
chcp 65001 > nul
echo ========================================================
echo Iniciando limpeza e organizacao automatica do projeto...
echo ========================================================

REM 1. Criando as pastas organizadas
if not exist data mkdir data
if not exist exports\pdf mkdir exports\pdf
if not exist exports\excel mkdir exports\excel
if not exist templates mkdir templates

echo.
echo [1/3] Movendo arquivos de dados e banco de dados...
if exist meu_estoque.db move meu_estoque.db data\
if exist view_acessorios.csv move view_acessorios.csv data\
if exist historico_movimentacoes.csv move historico_movimentacoes.csv data\
if exist Perfis.xlsx move Perfis.xlsx data\

echo.
echo [2/3] Movendo o arquivo visual (HTML)...
if exist index.html move index.html templates\

echo.
echo [3/3] Removendo arquivos temporarios e lixo (cache)...
if exist banco.sqbpro del banco.sqbpro
for /d /r %%i in (__pycache__) do @if exist "%%i" rmdir /s /q "%%i"

echo ========================================================
echo [SUCESSO] Faxina concluida com sucesso!
echo - Sua pasta 'uploads' foi mantida intacta na raiz.
echo - Banco de dados e CSVs foram movidos para a pasta \data
echo - O 'index.html' foi movido para a pasta \templates
echo ========================================================
pause