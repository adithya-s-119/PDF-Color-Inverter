@echo off
setlocal EnableExtensions

title PDF Color Inverter - Windows Build

echo ============================================================
echo   PDF Color Inverter 1.0 - Windows Build
echo ============================================================
echo.

set "PYTHON="

where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3.13 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON=%%P"
)

if not defined PYTHON if exist "C:\Python313\python.exe" set "PYTHON=C:\Python313\python.exe"

if not defined PYTHON (
    echo ERROR: Normal CPython 3.13 was not found.
    echo Do not use Python 3.14t/free-threaded for this build.
    pause
    exit /b 1
)

echo Using Python: %PYTHON%
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python 3.13 virtual environment...
    "%PYTHON%" -m venv .venv
    if errorlevel 1 goto :error
)

set "VENV=%CD%\.venv\Scripts\python.exe"

if not exist "%VENV%" (
    echo ERROR: Virtual environment was not created.
    goto :error
)

echo [1/6] Updating pip...
"%VENV%" -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [2/6] Installing Python dependencies...
"%VENV%" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/6] Preparing Tesseract OCR...

if not exist "runtime\tesseract\tesseract.exe" (
    if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" (
        echo Found Tesseract in Program Files.
        xcopy "%ProgramFiles%\Tesseract-OCR" "runtime\tesseract\" /E /I /Y /Q >nul
    ) else if exist "%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe" (
        echo Found Tesseract in Program Files x86.
        xcopy "%ProgramFiles(x86)%\Tesseract-OCR" "runtime\tesseract\" /E /I /Y /Q >nul
    ) else (
        where winget >nul 2>nul
        if errorlevel 1 (
            echo ERROR: Tesseract was not found and WinGet is unavailable.
            echo Install Tesseract OCR, then run this script again.
            goto :error
        )

        echo Installing Tesseract OCR with WinGet...
        winget install -e --id tesseract-ocr.tesseract --silent --accept-package-agreements --accept-source-agreements
        if errorlevel 1 goto :error

        if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" (
            xcopy "%ProgramFiles%\Tesseract-OCR" "runtime\tesseract\" /E /I /Y /Q >nul
        ) else if exist "%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe" (
            xcopy "%ProgramFiles(x86)%\Tesseract-OCR" "runtime\tesseract\" /E /I /Y /Q >nul
        ) else (
            echo ERROR: Tesseract executable was not found after installation.
            goto :error
        )
    )
)

if not exist "runtime\tesseract\tesseract.exe" (
    echo ERROR: Tesseract executable is missing.
    goto :error
)

if exist "runtime\tesseract\tessdata" rmdir /S /Q "runtime\tesseract\tessdata"
mkdir "runtime\tesseract\tessdata"

if errorlevel 1 (
    echo ERROR: Could not create runtime\tesseract\tessdata.
    goto :error
)

echo [4/6] Downloading English and Malayalam OCR models...

call :download "https://raw.githubusercontent.com/tesseract-ocr/tessdata/main/eng.traineddata" "runtime\tesseract\tessdata\eng.traineddata"
if errorlevel 1 (
    echo ERROR: Failed to download eng.traineddata.
    goto :error
)

call :download "https://raw.githubusercontent.com/tesseract-ocr/tessdata/main/mal.traineddata" "runtime\tesseract\tessdata\mal.traineddata"
if errorlevel 1 (
    echo ERROR: Failed to download mal.traineddata.
    goto :error
)

for %%F in ("runtime\tesseract\tessdata\eng.traineddata" "runtime\tesseract\tessdata\mal.traineddata") do (
    if not exist "%%~F" (
        echo ERROR: Missing OCR model: %%~F
        goto :error
    )
    for %%A in ("%%~F") do if %%~zA LSS 100000 (
        echo ERROR: OCR model looks incomplete: %%~F
        goto :error
    )
)

echo OCR models are ready.

echo [5/6] Preparing Malayalam font...
if exist "runtime\fonts\NotoSansMalayalam-Regular.ttf" goto :font_ready

mkdir "runtime\fonts" >nul 2>nul
call :download "https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSansMalayalam/NotoSansMalayalam-Regular.ttf" "runtime\fonts\NotoSansMalayalam-Regular.ttf"
if errorlevel 1 (
    echo ERROR: Failed to download Noto Sans Malayalam font.
    goto :error
)

:font_ready
if not exist "runtime\fonts\NotoSansMalayalam-Regular.ttf" (
    echo ERROR: Missing runtime\fonts\NotoSansMalayalam-Regular.ttf
    goto :error
)

for %%A in ("runtime\fonts\NotoSansMalayalam-Regular.ttf") do if %%~zA LSS 50000 (
    echo ERROR: Malayalam font looks incomplete.
    goto :error
)

echo [6/6] Building standalone EXE...
"%VENV%" -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error

"%VENV%" -m PyInstaller ^
 --noconfirm ^
 --clean ^
 --onefile ^
 --windowed ^
 --name PDFColorInverter ^
 --add-data "runtime\tesseract;tesseract" ^
 --add-data "runtime\fonts;fonts" ^
 --collect-all customtkinter ^
 app.py
if errorlevel 1 goto :error

if not exist "dist\PDFColorInverter.exe" (
    echo ERROR: PyInstaller did not create dist\PDFColorInverter.exe
    goto :error
)

echo.
echo ============================================================
echo BUILD COMPLETE
echo ============================================================
echo EXE: %CD%\dist\PDFColorInverter.exe
echo.
pause
exit /b 0

:download
set "URL=%~1"
set "OUT=%~2"

if not defined URL (
    echo ERROR: Download URL is empty.
    exit /b 1
)
if not defined OUT (
    echo ERROR: Download output path is empty.
    exit /b 1
)

if exist "%OUT%" del /Q "%OUT%" >nul 2>nul

for %%D in ("%OUT%") do if not exist "%%~dpD" mkdir "%%~dpD" >nul 2>nul

echo Downloading %OUT% ...

where curl.exe >nul 2>nul
if not errorlevel 1 (
    curl.exe -L --fail --retry 7 --retry-all-errors --retry-delay 3 ^
      --connect-timeout 30 --max-time 600 ^
      -A "Mozilla/5.0" "%URL%" -o "%OUT%"
    if not errorlevel 1 if exist "%OUT%" exit /b 0
    echo curl failed. Trying PowerShell...
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$u='%URL%'; $o='%OUT%'; $ok=$false; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; " ^
  "for($i=1;$i -le 7;$i++){try{Invoke-WebRequest -UseBasicParsing -Headers @{'User-Agent'='Mozilla/5.0'} -Uri $u -OutFile $o -TimeoutSec 600; if((Get-Item $o).Length -gt 100000){$ok=$true;break}}catch{Write-Host ('Retry '+$i+': '+$_.Exception.Message)}; Start-Sleep -Seconds 3}; " ^
  "if(-not $ok){if(Test-Path $o){Remove-Item $o -Force};exit 1}"

if not exist "%OUT%" exit /b 1
exit /b 0

:error
echo.
echo ============================================================
echo BUILD FAILED
echo ============================================================
echo.
pause
exit /b 1
