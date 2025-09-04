@echo off
setlocal enabledelayedexpansion

rem === 基本路径 ===
set "BASEDIR=%~dp0"
set "BASEDIR=%BASEDIR:~0,-1%"
set "VENV=%BASEDIR%\.venv"
set "OUTDIR=%BASEDIR%\outputs"

rem === 输入 zip（按需修改文件名或放入 %BASEDIR%） ===
set "INPUT=%BASEDIR%\2.000000-AXIAL SC-25389.zip"

echo [%%date%% %%time%%] start 
echo PYTHON: %VENV%\Scripts\python.exe
echo INPUT : %INPUT%
echo OUTDIR: %OUTDIR%
echo.

rem === 1) 创建 venv（若不存在） ===
if not exist "%VENV%\Scripts\python.exe" (
  echo [+] Creating venv...
  python -m venv "%VENV%"
)

rem === 2) 装依赖（仅首次/有缺包时） ===
echo [+] Installing deps (if needed)...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
"%VENV%\Scripts\python.exe" -m pip install -r "%BASEDIR%\requirements-py313.txt"
if errorlevel 1 (
  echo [!] pip install failed. See errors above.
  exit /b 1
)

rem === 3) 运行主流程 ===
echo [+] Running main.py ...
"%VENV%\Scripts\python.exe" "%BASEDIR%\main.py" --input "%INPUT%" --out "%OUTDIR%"
if errorlevel 1 (
  echo [!] main.py failed. EXITCODE=%errorlevel%
  exit /b %errorlevel%
)

rem === 4) 生成 PDF 报告（关键就这一步） ===
echo [+] Generating PDF report ...
"%VENV%\Scripts\python.exe" "%BASEDIR%\make_pdf.py" --in_dir "%OUTDIR%"
if errorlevel 1 (
  echo [!] make_pdf.py failed. EXITCODE=%errorlevel%
  exit /b %errorlevel%
)

rem === 5) 自动打开最新 PDF（可选） ===
set "LATEST_PDF="
for /f "delims=" %%P in ('dir /b /o:-d "%OUTDIR%\*_report.pdf" 2^>nul') do (
  set "LATEST_PDF=%OUTDIR%\%%P"
  goto :OPENPDF
)
:OPENPDF
if defined LATEST_PDF (
  echo [+] Opening: %LATEST_PDF%
  start "" "%LATEST_PDF%"
) else (
  echo [i] No PDF found in %OUTDIR%.
)

echo [+] Done.
exit /b 0
