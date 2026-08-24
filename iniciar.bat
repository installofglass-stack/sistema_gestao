@echo off
title Sistema de Acessorios e Perfis
color 0A
echo ========================================================
echo Iniciando o Sistema de Cadastro de Acessorios...
echo Pressione Ctrl+C se quiser fechar o servidor a qualquer momento.
echo ========================================================
echo.

:: Verifica se o Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: O Python nao foi encontrado ou nao esta instalado!
    echo Instale o Python e marque a opcao "Add Python to PATH".
    pause
    exit
)

:: Inicia o aplicativo Flask
python app.py

pause