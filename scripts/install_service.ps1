# Installs CDG Windows Agent as a Windows Service using NSSM.
# The service runs as the 'agent' user (not LocalSystem — Session 0 has no UI).
# Run as Administrator.
#
# NSSM download: https://nssm.cc/download

param(
    [string]$ServiceName = "CDGAgent",
    [string]$PythonExe = "C:\Python312\python.exe",
    [string]$ScriptPath = "C:\cdg\server\main.py",
    [string]$AppDir = "C:\cdg",
    [string]$AgentUser = "agent",
    [string]$AgentPassword = $(throw "Provide -AgentPassword"),
    [string]$NssmPath = "C:\tools\nssm\nssm.exe"
)

if (-not (Test-Path $NssmPath)) {
    Write-Error "NSSM not found at $NssmPath. Download from https://nssm.cc/download"
    exit 1
}

& $NssmPath install $ServiceName $PythonExe $ScriptPath
& $NssmPath set $ServiceName AppDirectory $AppDir
& $NssmPath set $ServiceName AppStdout "$AppDir\logs\stdout.log"
& $NssmPath set $ServiceName AppStderr "$AppDir\logs\stderr.log"
& $NssmPath set $ServiceName AppStdoutCreationDisposition 4   # append
& $NssmPath set $ServiceName AppStderrCreationDisposition 4
& $NssmPath set $ServiceName ObjectName ".\$AgentUser" $AgentPassword
& $NssmPath set $ServiceName Start SERVICE_AUTO_START
& $NssmPath set $ServiceName AppRestartDelay 3000

New-Item -ItemType Directory -Force -Path "$AppDir\logs" | Out-Null

& $NssmPath start $ServiceName
Write-Host "Service '$ServiceName' installed and started as user '$AgentUser'."
Write-Host "Logs: $AppDir\logs\"
