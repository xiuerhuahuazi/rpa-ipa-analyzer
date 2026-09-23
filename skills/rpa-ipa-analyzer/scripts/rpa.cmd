@echo off
rem ============================================================================
rem  rpa.cmd - DSH launcher for rpa-ipa-analyzer (Windows)
rem
rem  Usage (from a pwsh command):
rem    & "<SK>\scripts\rpa.cmd" extract  "<project>" --force
rem    & "<SK>\scripts\rpa.cmd" skeleton "<project>" --depth standard
rem    & "<SK>\scripts\rpa.cmd" stats    "<project>"
rem    & "<SK>\scripts\rpa.cmd" list     "<project>" --format json
rem
rem  All arguments are forwarded verbatim to extract_nodes.py.
rem
rem  Why this launcher exists (see DSH.md):
rem    1. DSH runs every command in a FRESH shell process, so a $PY variable
rem       resolved in one call is gone by the next. This resolves every time.
rem    2. On machines with no real Python - `python` / `python3` resolve to the
rem       Microsoft Store App Execution Alias stubs, which exit 9009, and `py`
rem       may report "No installed Python found!" - the upstream-documented
rem       `python3 scripts/extract_nodes.py` form cannot run at all.
rem    3. `-X utf8` is mandatory. Without it Python encodes stdout with the
rem       ANSI code page (GBK on zh-CN Windows) and Chinese node names reach the
rem       agent's context as mojibake, silently corrupting every report.
rem
rem  Interpreter search order:
rem    %RPA_IPA_PYTHON%  ->  .venv-py38 | .venv | venv under %CD% and its parents
rem                      ->  python3 | python on PATH  ->  py -3
rem  Every candidate is validated as Python >= 3.8 before it is accepted.
rem ============================================================================
setlocal EnableDelayedExpansion
set "SCRIPT=%~dp0extract_nodes.py"
set "PY="
set "PYARG="

if not exist "%SCRIPT%" (
  echo [rpa.cmd] not found: %SCRIPT% 1>&2
  exit /b 2
)

rem ---- 1. explicit override -------------------------------------------------
if defined RPA_IPA_PYTHON (
  if exist "%RPA_IPA_PYTHON%" (
    set "PY=%RPA_IPA_PYTHON%"
    goto :run
  )
  echo [rpa.cmd] warning: RPA_IPA_PYTHON does not exist: %RPA_IPA_PYTHON% 1>&2
)

rem ---- 2. a venv at %CD% or in an ancestor directory ------------------------
set "D=%CD%"
for /L %%i in (1,1,6) do (
  if not defined PY (
    if exist "!D!\.venv-py38\Scripts\python.exe" set "PY=!D!\.venv-py38\Scripts\python.exe"
    if not defined PY if exist "!D!\.venv\Scripts\python.exe" set "PY=!D!\.venv\Scripts\python.exe"
    if not defined PY if exist "!D!\venv\Scripts\python.exe" set "PY=!D!\venv\Scripts\python.exe"
    for %%P in ("!D!\..") do set "D=%%~fP"
  )
)
if defined PY goto :run

rem ---- 3. a working interpreter on PATH ------------------------------------
for %%C in (python3.exe python.exe) do (
  if not defined PY (
    for /f "delims=" %%W in ('where %%C 2^>nul') do (
      if not defined PY (
        "%%W" -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 3)" >nul 2>&1
        if not errorlevel 1 set "PY=%%W"
      )
    )
  )
)
if defined PY goto :run

rem ---- 4. the py launcher ---------------------------------------------------
py -3 -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 3)" >nul 2>&1
if not errorlevel 1 (
  set "PY=py"
  set "PYARG=-3"
)
if defined PY goto :run

echo [rpa.cmd] no Python 3.8+ interpreter found. 1>&2
echo   Fix: set RPA_IPA_PYTHON to a python.exe, 1>&2
echo        or create .venv-py38 in the project directory. 1>&2
exit /b 127

:run
rem Disable delayed expansion before forwarding args, so that a literal '!' in a
rem path survives. setlocal copies the environment, so %PY% still resolves.
setlocal DisableDelayedExpansion
"%PY%" %PYARG% -X utf8 "%SCRIPT%" %*
exit /b %ERRORLEVEL%
