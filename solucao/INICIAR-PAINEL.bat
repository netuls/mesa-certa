@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo       MESA CERTA - PAINEL COMERCIAL
echo ============================================
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo ERRO: Python nao foi encontrado.
  echo Instale o Python 3.10 ou superior em https://www.python.org/downloads/
  echo Durante a instalacao, marque "Add Python to PATH".
  pause
  exit /b 1
)
if not exist "index.html" (
  echo ERRO: index.html nao encontrado nesta pasta.
  echo Deixe index.html junto do app.py e mesa_certa.db.
  pause
  exit /b 1
)
if not exist "app.py" (
  echo ERRO: app.py nao encontrado nesta pasta.
  pause
  exit /b 1
)
if not exist "mesa_certa.db" (
  echo ERRO: mesa_certa.db nao encontrado nesta pasta.
  pause
  exit /b 1
)
echo Carregando os pedidos do formulario...
python importar_lote.py
echo.
echo Iniciando o servidor. Nao feche esta janela enquanto usar o painel.
start "" /b cmd /c "timeout /t 2 /nobreak ^>nul ^& start http://127.0.0.1:8080"
python app.py
if errorlevel 1 (
  echo.
  echo O servidor encerrou com erro. Confira a mensagem acima.
  pause
)
