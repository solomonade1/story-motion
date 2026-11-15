param(
  [Parameter(Mandatory = $true)][string]$TextsJson,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [string]$Voice = "Microsoft David Desktop",
  [int]$Rate = 0
)
# Local, offline text-to-speech via the Windows SAPI voice installed on this machine.
# Used ONLY to create a development narration fixture. Text is read from a JSON file, never
# interpolated into a command line.
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$texts = Get-Content -Raw -Encoding UTF8 -Path $TextsJson | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($Voice)
$synth.Rate = $Rate
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$i = 0
foreach ($t in $texts) {
  $path = Join-Path $OutDir ("line-{0:D2}.wav" -f $i)
  $synth.SetOutputToWaveFile($path, $fmt)
  $synth.Speak([string]$t)
  $synth.SetOutputToNull()
  $i++
}
$synth.Dispose()
Write-Output "wrote $i files"
