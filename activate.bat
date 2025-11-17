@echo off
cd "C:\Users\andre" 
echo Cambiando a C:\Users\andre para la activacion...

call venv\Scripts\Activate

cd "C:\Users\andre\OneDrive\Documentos\DesarrolloWeb3"

echo.
echo Entorno virtual activado.
echo Directorio actual: %cd%

:end