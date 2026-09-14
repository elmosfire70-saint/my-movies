# 설치된 ComfyUI 파이썬 환경으로 로컬 영상 제작 명령을 실행한다.
param(
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet('pipeline', 'project', 'test')]
    [string]$Tool,
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$ToolArguments
)
$runtime = 'E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe'
$env:PYTHONIOENCODING = 'utf-8'
Push-Location $PSScriptRoot
try {
    if ($Tool -eq 'test') {
        & $runtime -m unittest -v test_pipeline test_project
    } else {
        & $runtime (Join-Path $PSScriptRoot ($Tool + '.py')) @ToolArguments
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
