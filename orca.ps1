$ScriptPath = Join-Path $PSScriptRoot ".agents\scripts\orca.py"
python -X utf8 $ScriptPath $args
