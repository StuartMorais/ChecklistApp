param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^v\d+\.\d+\.\d+$')]
    [string]$Version,

    [switch]$SkipInstaller
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$VersionNumber = $Version.TrimStart('v')
$ReleaseDir = Join-Path $ProjectRoot 'dist\release'
$IconPath = Join-Path $ProjectRoot 'assets\icon.ico'

if (-not (Test-Path $IconPath)) {
    throw "Icon not found: $IconPath"
}

Push-Location $ProjectRoot
try {
    Remove-Item -Recurse -Force 'build', 'dist' -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

    python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name 'ChecklistPython' `
        --icon $IconPath `
        --add-data "assets;assets" `
        'main.py'

    $BuiltExe = Join-Path $ProjectRoot 'dist\ChecklistPython.exe'

    if (-not (Test-Path $BuiltExe)) {
        throw "PyInstaller did not create $BuiltExe"
    }

    $PortableExe = Join-Path $ReleaseDir "ChecklistPython-$Version.exe"
    Copy-Item $BuiltExe $PortableExe -Force

    if (-not $SkipInstaller) {
        $Iscc = Get-Command 'iscc.exe' -ErrorAction SilentlyContinue

        if (-not $Iscc) {
            $PossibleIscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'

            if (Test-Path $PossibleIscc) {
                $Iscc = Get-Item $PossibleIscc
            }
        }

        if ($Iscc) {
            $IsccPath = if ($Iscc.PSObject.Properties.Name -contains 'Source') {
                $Iscc.Source
            } else {
                $Iscc.FullName
            }

            & $IsccPath "/DMyAppVersion=$VersionNumber" 'installer\ChecklistPython.iss'
        } else {
            Write-Warning 'Inno Setup was not found. Skipping installer build.'
        }
    }

    $Assets = Get-ChildItem $ReleaseDir -File -Filter '*.exe' | Sort-Object Name
    $HashFile = Join-Path $ReleaseDir 'SHA256SUMS.txt'
    $HashLines = foreach ($Asset in $Assets) {
        $Hash = (Get-FileHash $Asset.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        "$Hash  $($Asset.Name)"
    }

    $HashLines | Set-Content -Path $HashFile -Encoding utf8

    Write-Host "Release files:"
    Get-ChildItem $ReleaseDir -File | Sort-Object Name | ForEach-Object {
        Write-Host " - $($_.FullName)"
    }
}
finally {
    Pop-Location
}
