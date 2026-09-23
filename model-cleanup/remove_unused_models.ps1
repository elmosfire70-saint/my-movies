# 저장된 워크플로에서 쓰지 않는 모델 8개만 재검증한 뒤 삭제한다.
param([switch]$Execute)
$ErrorActionPreference = 'Stop'

$folder = Split-Path -Parent $MyInvocation.MyCommand.Path
$inventory = Get-Content -LiteralPath (Join-Path $folder 'inventory.json') -Raw | ConvertFrom-Json
$workflowRoot = 'E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\user\default\workflows'
$roots = @(
    'E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\models',
    'J:\LTX2.5'
)
$expected = @(
    'minimax_h3_fl2va_pruned_int8_convrot.safetensors',
    'qwen_2.5_vl_7b_fp8_scaled.safetensors',
    'qwen_image_vae.safetensors',
    'ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors',
    'ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors',
    'gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors',
    'ltx-2.5-audio-vae-bf16.safetensors',
    'ltx-2.5-video-vae-conv-bf16.safetensors'
)
$candidates = @($inventory.models | Where-Object { $_.saved_workflows.Count -eq 0 })
$names = @( $candidates | ForEach-Object { [IO.Path]::GetFileName($_.path) } | Sort-Object )
if (($names -join '|') -ne (($expected | Sort-Object) -join '|')) {
    throw 'Inventory candidate set changed.'
}
$workflowFiles = @(Get-ChildItem -LiteralPath $workflowRoot -Recurse -File -Filter '*.json')
if ($workflowFiles.Count -ne $inventory.workflow_count) {
    throw 'Saved workflow count changed.'
}
$workflowText = @($workflowFiles | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw })
$checked = @()
foreach ($row in $candidates) {
    $path = [IO.Path]::GetFullPath($row.path)
    $allowed = $false
    foreach ($root in $roots) {
        $prefix = [IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
        if ($path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            $allowed = $true
        }
    }
    if (-not $allowed -or [IO.Path]::GetExtension($path) -ne '.safetensors') {
        throw "Unexpected target path: $path"
    }
    $item = Get-Item -LiteralPath $path
    if ($item.PSIsContainer -or $item.LinkType -or $item.Length -ne $row.bytes) {
        throw "Target changed: $path"
    }
    foreach ($content in $workflowText) {
        if ($content.IndexOf($item.Name, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
            throw "Saved workflow now uses: $path"
        }
    }
    $checked += [pscustomobject]@{ path = $path; bytes = $item.Length }
}
$sum = ($checked | Measure-Object -Property bytes -Sum).Sum
Write-Output "Checked $($checked.Count) unused model files, $([math]::Round($sum / 1GB, 2)) GiB."
if (-not $Execute) {
    $checked | ForEach-Object { Write-Output $_.path }
    return
}

$before = Join-Path $folder 'inventory-before.json'
if (Test-Path -LiteralPath $before) {
    throw "Backup already exists: $before"
}
Copy-Item -LiteralPath (Join-Path $folder 'inventory.json') -Destination $before
$deleted = @()
try {
    foreach ($row in $checked) {
        Remove-Item -LiteralPath $row.path -Force
        $deleted += $row
        Write-Output "Deleted $($row.path)"
    }
} finally {
    [pscustomobject]@{
        timestamp = (Get-Date).ToString('o')
        saved_workflows_checked = $workflowFiles.Count
        deleted = $deleted
        deleted_bytes = ($deleted | Measure-Object -Property bytes -Sum).Sum
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $folder 'deletion-report.json') -Encoding UTF8
}
