@echo off
REM  === Crear entorno virtual usando Python ===
python.exe -m venv venv
python.exe --version

REM === Activar entorno virtual (solo para esta terminal) ===
call venv\Scripts\activate

REM === Actualizar pip y setuptools ===
python -m pip install --upgrade pip setuptools

REM === Instalar dependencias básicas ===
pip install streamlit gpxpy pyproj pandas numpy altair pydeck scipy requests haversine matplotlib

REM === Guardar requerimientos ===
:: pip freeze > requirements.txt

echo.
echo ✅ Entorno virtual creado y paquetes instalados.
echo 👉 Para usarlo en el futuro:
echo     venv\Scripts\activate
echo     streamlit run maxsail-analytics.py
pause
