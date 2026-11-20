@echo off
chcp 65001 >nul
setlocal

echo ============================================================
echo   MERGESORT CUTOFF (JAVA) - FULL REPRODUCTION PIPELINE
echo ============================================================

where javac >nul 2>&1
if errorlevel 1 (
    echo [LOI] Khong tim thay javac. Hay cai dat JDK 17+ va them vao PATH.
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo [LOI] Khong tim thay python. Hay cai dat Python 3 va them vao PATH.
    exit /b 1
)

if not exist out mkdir out

echo [1/6] Kiem tra thu vien Python...
python -c "import numpy, pandas, matplotlib" >nul 2>&1
if errorlevel 1 (
    echo Dang cai dat thu vien tu requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 exit /b 1
)

echo [2/6] Thu thap cau hinh may va JDK...
python scripts\collect_machine.py
if errorlevel 1 exit /b 1

echo [3/6] Sinh 16 bo du lieu thi nghiem...
python scripts\generate_data.py
if errorlevel 1 exit /b 1

echo [4/6] Bien dich ma nguon Java...
javac -encoding UTF-8 -d out src\Insertion.java src\Merge.java src\BenchmarkRunner.java
if errorlevel 1 exit /b 1

echo [5/6] Chay benchmark Java (4,080 luot do)...
java -Xms2g -Xmx4g -cp out BenchmarkRunner
if errorlevel 1 exit /b 1

echo [6/6] Phan tich thong ke, ve 5 bieu do va tao bao cao...
python scripts\analyze_and_plot.py
if errorlevel 1 exit /b 1

python scripts\build_docs.py
if errorlevel 1 exit /b 1

echo ============================================================
echo   HOAN TAT! Kiem tra:
echo   - README.md
echo   - report\BaoCao_MergeSort_Cutoff.md
echo   - results\charts\ (5 bieu do)
echo   - data\ (16 bo du lieu)
echo ============================================================
endlocal
