@echo off
setlocal enabledelayedexpansion

rem AS 1288 Glass Thickness Calculator - Full Regression Runner (Windows)
rem Runs all 8 tracked test suites in one command:
rem   - 5 pytest suites (test_pathway3, test_pathway4, test_silicone_bite,
rem     test_structural_glazing, test_table_5_3)
rem   - 3 standalone script-style test files (test_runner, test_runner_2,
rem     test_structural_consistency) - these are NOT pytest-discoverable
rem     and do not exit non-zero on failure, so pass/fail is determined by
rem     grepping their stdout for their own known success line.

rem cd to repo root using this script's own location, regardless of caller's cwd
cd /d "%~dp0"

set PYTHON=python
if exist ".venv\Scripts\python.exe" set PYTHON=.venv\Scripts\python.exe

set STEP1=FAIL
set STEP2=FAIL
set STEP3=FAIL
set STEP4=FAIL

echo ============================================================
echo   STEP 1/4: pytest suites (pathway3, pathway4, silicone_bite,
echo             structural_glazing, table_5_3)
echo ============================================================
"%PYTHON%" -m pytest tests/test_pathway3.py tests/test_pathway4.py tests/test_silicone_bite.py tests/test_structural_glazing.py tests/test_table_5_3.py -v
if %errorlevel% equ 0 set STEP1=PASS

echo.
echo ============================================================
echo   STEP 2/4: test_runner.py
echo ============================================================
"%PYTHON%" tests/test_runner.py > "%TEMP%\run_tests_step2.txt" 2>&1
type "%TEMP%\run_tests_step2.txt"
findstr /C:"ALL TEST CASES PASSED" "%TEMP%\run_tests_step2.txt" >nul
if %errorlevel% equ 0 set STEP2=PASS
del "%TEMP%\run_tests_step2.txt" >nul 2>&1

echo.
echo ============================================================
echo   STEP 3/4: test_runner_2.py
echo ============================================================
"%PYTHON%" tests/test_runner_2.py > "%TEMP%\run_tests_step3.txt" 2>&1
type "%TEMP%\run_tests_step3.txt"
findstr /C:"ALL NEW TEST CASES PASSED" "%TEMP%\run_tests_step3.txt" >nul
if %errorlevel% equ 0 set STEP3=PASS
del "%TEMP%\run_tests_step3.txt" >nul 2>&1

echo.
echo ============================================================
echo   STEP 4/4: test_structural_consistency.py
echo ============================================================
"%PYTHON%" tests/test_structural_consistency.py > "%TEMP%\run_tests_step4.txt" 2>&1
type "%TEMP%\run_tests_step4.txt"
findstr /C:"ALL STRUCTURAL CHECKS PASSED" "%TEMP%\run_tests_step4.txt" >nul
if %errorlevel% equ 0 set STEP4=PASS
del "%TEMP%\run_tests_step4.txt" >nul 2>&1

echo.
echo ============================================================
echo   REGRESSION SUMMARY
echo ============================================================
echo   1. pytest suites (5)              : !STEP1!
echo   2. test_runner.py                 : !STEP2!
echo   3. test_runner_2.py               : !STEP3!
echo   4. test_structural_consistency.py : !STEP4!
echo ============================================================

if "!STEP1!!STEP2!!STEP3!!STEP4!"=="PASSPASSPASSPASS" (
    echo   OVERALL: ALL 8 SUITES PASSED
    exit /b 0
) else (
    echo   OVERALL: FAILURE DETECTED - see steps marked FAIL above
    exit /b 1
)
