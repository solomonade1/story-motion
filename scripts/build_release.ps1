<#
.SYNOPSIS
  Assembles the portable Windows release folder (and zip): private Python + worker + built UI + FFmpeg.
.DESCRIPTION
  Run from the repository root AFTER `npm ci && npm run build` in apps\desktop. CI runs this for you
  (.github/workflows/release.yml). Needs: the same Python version installed as -PythonVersion (for tkinter files), internet.
.EXAMPLE
  .\scripts\build_release.ps1 -Version 0.1.0
#>
param(
  [Parameter(Mandatory)][string]$Version,
  [string]$PythonVersion = "3.12.10",
  [string]$OutDir = "dist-release",
  [string]$FfmpegUrl = "https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-full_build.zip",
  [string]$FfmpegSha256 = "759d0a9831c436a0eb331ad36f236c06cb04aaa0005da46571f0e9d3d9206f6b"
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$name = "StoryMotion-Studio-$Version-win64"
$root = Join-Path $repo "$OutDir\$name"
$dl = Join-Path $repo "$OutDir\_downloads"
if (Test-Path $root) { Remove-Item $root -Recurse -Force }
if (Test-Path "$OutDir\_downloadsfmpeg-x") { Remove-Item "$OutDir\_downloadsfmpeg-x" -Recurse -Force }
New-Item -ItemType Directory -Force $root, $dl | Out-Null

if (-not (Test-Path "apps\desktop\dist\index.html")) { throw "UI not built. Run: cd apps\desktop; npm ci; npm run build" }

# 1. Private Python (embeddable) -----------------------------------------------------------------------------
$py = Join-Path $root "python"
$embedZip = Join-Path $dl "python-embed.zip"
Invoke-WebRequest "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip" -OutFile $embedZip
Expand-Archive $embedZip $py
$tag = ($PythonVersion -split "\.")[0..1] -join ""
@("python$tag.zip", ".", "..\app\workers\media", "Lib\site-packages", "import site") | Set-Content (Join-Path $py "python$tag._pth") -Encoding ascii

# tkinter (the native file chooser) is not in the embeddable build: copy it from the matching full install.
$full = (& python -c "import sys; print(sys.base_prefix)").Trim()
$fullVer = (& python -c "import platform; print(platform.python_version())").Trim()
if ($fullVer -ne $PythonVersion) { throw "Build Python is $fullVer but -PythonVersion is $PythonVersion; they must match exactly." }
New-Item -ItemType Directory -Force (Join-Path $py "Lib\site-packages") | Out-Null
Copy-Item "$full\Lib\tkinter" (Join-Path $py "Lib\site-packages\tkinter") -Recurse
Copy-Item "$full\DLLs\_tkinter.pyd", "$full\DLLs\tcl86t.dll", "$full\DLLs\tk86t.dll" $py
if (Test-Path "$full\DLLs\zlib1.dll") { Copy-Item "$full\DLLs\zlib1.dll" $py }
Copy-Item "$full\tcl" (Join-Path $py "tcl") -Recurse
Get-ChildItem (Join-Path $py "Lib\site-packages\tkinter") -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem (Join-Path $py "tcl") -Recurse -Directory -Include "demos","tzdata" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

# 2. Third-party Python packages (binary wheels only; no compiling) -----------------------------------------------
$ErrorActionPreference = "Continue"   # Windows PowerShell 5.1 treats any native stderr (pip notices) as an error; we check exit codes instead
& python -m pip install --quiet --disable-pip-version-check --target (Join-Path $py "Lib\site-packages") --only-binary=:all: --no-compile "pydantic>=2.6" "pillow>=10"
$pipExit = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($pipExit) { throw "pip install failed (exit $pipExit)" }

# 3. The app: worker source, built UI, icon (layout matters: the code finds the UI and FFmpeg relative to app\) ----------
$app = Join-Path $root "app"
New-Item -ItemType Directory -Force "$app\workers\media", "$app\apps\desktop", "$app\tools\ffmpeg\bin" | Out-Null
Copy-Item "workers\media\storymotion_media" "$app\workers\media\storymotion_media" -Recurse
Copy-Item "apps\desktop\dist" "$app\apps\desktop\dist" -Recurse
Copy-Item "apps\desktop\src-tauri\icons\icon.ico" "$app\icon.ico"
Get-ChildItem $app -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# 4. FFmpeg (pinned + checksum-verified) -----------------------------------------------------------------------------
$ffZip = Join-Path $dl "ffmpeg.zip"
Invoke-WebRequest $FfmpegUrl -OutFile $ffZip
$got = (Get-FileHash $ffZip -Algorithm SHA256).Hash.ToLower()
if ($got -ne $FfmpegSha256.ToLower()) { throw "FFmpeg checksum mismatch: expected $FfmpegSha256, got $got" }
$ffx = Join-Path $dl "ffmpeg-x"
if (Test-Path $ffx) { Remove-Item $ffx -Recurse -Force }
Expand-Archive $ffZip $ffx
$ffroot = Get-ChildItem $ffx -Directory | Select-Object -First 1
Copy-Item "$($ffroot.FullName)\bin\ffmpeg.exe", "$($ffroot.FullName)\bin\ffprobe.exe" "$app\tools\ffmpeg\bin"
New-Item -ItemType Directory -Force "$root\licenses" | Out-Null
Get-ChildItem $ffroot.FullName -File | Where-Object { $_.Name -match "LICENSE|README" } | Copy-Item -Destination "$root\licenses" -ErrorAction SilentlyContinue
Copy-Item "$($ffroot.FullName)\LICENSE" "$root\licenses\FFmpeg-LICENSE.txt" -ErrorAction SilentlyContinue

# 5. Launchers + docs ----------------------------------------------------------------------------------------------
Copy-Item "packaging\templates\*" $root
Copy-Item "packaging\USER_GUIDE.md" "$root\USER GUIDE.md"
Copy-Item "packaging\THIRD_PARTY_NOTICES.md" "$root\licenses\THIRD_PARTY_NOTICES.md"
Set-Content "$root\VERSION.txt" "StoryMotion Studio $Version`nPython $PythonVersion`nFFmpeg: $FfmpegUrl`n" -Encoding ascii

# 6. Smoke test the assembled bundle with ONLY its own runtime -----------------------------------------------------
$env:PYTHONHOME = $null; $env:PYTHONPATH = $null
$ErrorActionPreference = "Continue"
& "$py\python.exe" -c "import tkinter, pydantic, PIL, storymotion_media; print('imports ok')"
$e1 = $LASTEXITCODE
& "$py\python.exe" -m storymotion_media doctor
$e2 = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($e1) { throw "bundle import check failed" }
if ($e2) { throw "bundle doctor failed (FFmpeg/ffprobe not usable)" }

# 7. Zip + checksum --------------------------------------------------------------------------------------------------
$zip = Join-Path $repo "$OutDir\$name.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $root -DestinationPath $zip -CompressionLevel Optimal
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
"$hash  $name.zip" | Set-Content "$zip.sha256" -Encoding ascii
Write-Host "Built $zip ($([math]::Round((Get-Item $zip).Length/1MB)) MB)  sha256 $hash"
