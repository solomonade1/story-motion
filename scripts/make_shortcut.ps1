<#
.SYNOPSIS
  Creates a "StoryMotion Studio" shortcut that opens the app window (no console, own icon).
.EXAMPLE
  .\scripts\make_shortcut.ps1              # puts the shortcut in the project folder
  .\scripts\make_shortcut.ps1 -Desktop     # also on your Desktop
  .\scripts\make_shortcut.ps1 -StartMenu   # also in the Start menu (current user)
It only creates .lnk files where you ask; it changes no system setting.
#>
param([switch]$Desktop, [switch]$StartMenu)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$pyw = Join-Path $repo ".venv\Scripts\pythonw.exe"
$icon = Join-Path $repo "apps\desktop\src-tauri\icons\icon.ico"
$dist = Join-Path $repo "apps\desktop\dist\index.html"
if (-not (Test-Path $pyw)) { throw "Python environment not found at $pyw. Run the Setup steps in README.md first." }
if (-not (Test-Path $dist)) { throw "The app screens are not built. Run:  cd apps\desktop ; npm install ; npm run build" }
$targets = @((Join-Path $repo "StoryMotion Studio.lnk"))
if ($Desktop) { $targets += (Join-Path ([Environment]::GetFolderPath("Desktop")) "StoryMotion Studio.lnk") }
if ($StartMenu) { $targets += (Join-Path ([Environment]::GetFolderPath("Programs")) "StoryMotion Studio.lnk") }
$shell = New-Object -ComObject WScript.Shell
foreach ($t in $targets) {
  $lnk = $shell.CreateShortcut($t)
  $lnk.TargetPath = $pyw
  $lnk.Arguments = "-m storymotion_media launch"
  $lnk.WorkingDirectory = Join-Path $repo "workers\media"
  if (Test-Path $icon) { $lnk.IconLocation = $icon }
  $lnk.Description = "StoryMotion Studio"
  $lnk.Save()
  Write-Host "Created $t"
}
