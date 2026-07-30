#!/usr/bin/env bash
# AS 1288 Glass Thickness Calculator - Full Regression Runner (bash)
# Runs all 8 tracked test suites in one command:
#   - 5 pytest suites (test_pathway3, test_pathway4, test_silicone_bite,
#     test_structural_glazing, test_table_5_3)
#   - 3 standalone script-style test files (test_runner, test_runner_2,
#     test_structural_consistency) - these are NOT pytest-discoverable
#     and do not exit non-zero on failure, so pass/fail is determined by
#     grepping their stdout for their own known success line.

# cd to repo root using this script's own location, regardless of caller's cwd
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON=python
if [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
fi

STEP1=FAIL
STEP2=FAIL
STEP3=FAIL
STEP4=FAIL

echo "============================================================"
echo "  STEP 1/4: pytest suites (pathway3, pathway4, silicone_bite,"
echo "            structural_glazing, table_5_3)"
echo "============================================================"
"$PYTHON" -m pytest tests/test_pathway3.py tests/test_pathway4.py tests/test_silicone_bite.py tests/test_structural_glazing.py tests/test_table_5_3.py -v
if [ $? -eq 0 ]; then STEP1=PASS; fi

echo
echo "============================================================"
echo "  STEP 2/4: test_runner.py"
echo "============================================================"
STEP2_OUT="$("$PYTHON" tests/test_runner.py 2>&1)"
echo "$STEP2_OUT"
if echo "$STEP2_OUT" | grep -q "ALL TEST CASES PASSED"; then STEP2=PASS; fi

echo
echo "============================================================"
echo "  STEP 3/4: test_runner_2.py"
echo "============================================================"
STEP3_OUT="$("$PYTHON" tests/test_runner_2.py 2>&1)"
echo "$STEP3_OUT"
if echo "$STEP3_OUT" | grep -q "ALL NEW TEST CASES PASSED"; then STEP3=PASS; fi

echo
echo "============================================================"
echo "  STEP 4/4: test_structural_consistency.py"
echo "============================================================"
STEP4_OUT="$("$PYTHON" tests/test_structural_consistency.py 2>&1)"
echo "$STEP4_OUT"
if echo "$STEP4_OUT" | grep -q "ALL STRUCTURAL CHECKS PASSED"; then STEP4=PASS; fi

echo
echo "============================================================"
echo "  REGRESSION SUMMARY"
echo "============================================================"
echo "  1. pytest suites (5)              : $STEP1"
echo "  2. test_runner.py                 : $STEP2"
echo "  3. test_runner_2.py               : $STEP3"
echo "  4. test_structural_consistency.py : $STEP4"
echo "============================================================"

if [ "$STEP1$STEP2$STEP3$STEP4" = "PASSPASSPASSPASS" ]; then
    echo "  OVERALL: ALL 8 SUITES PASSED"
    exit 0
else
    echo "  OVERALL: FAILURE DETECTED - see steps marked FAIL above"
    exit 1
fi
