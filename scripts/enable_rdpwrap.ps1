# Installs RDP Wrapper Library to allow concurrent RDP sessions on consumer Windows.
# Run as Administrator. Re-run autoupdate.bat after every Windows update.
#
# RDP Wrapper Library: https://github.com/stascorp/rdpwrapper
# Updated ini: https://github.com/sebaxakerhtc/rdpwrap.ini

param(
    [string]$RDPWrapDir = "C:\tools\rdpwrap"
)

if (-not (Test-Path $RDPWrapDir)) {
    Write-Error "RDP Wrapper not found at $RDPWrapDir. Download and extract it first."
    exit 1
}

Push-Location $RDPWrapDir
.\install.bat
.\autoupdate.bat
.\RDPConf.exe
Pop-Location

Write-Host "RDP Wrapper installed. Verify all green in RDPConf.exe."
Write-Host "After any Windows update, re-run: $RDPWrapDir\autoupdate.bat"
