$ErrorActionPreference = 'Stop'
& node (Join-Path $PSScriptRoot 'ensure-backlogctl.js') @args
exit $LASTEXITCODE
