# Creates the 'agent' Windows user account used for isolated automation sessions.
# Run as Administrator.

param(
    [string]$Username = "agent",
    [string]$Password = $(throw "Provide -Password"),
    [switch]$AdminRights
)

$SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
New-LocalUser -Name $Username -Password $SecurePassword -PasswordNeverExpires
Add-LocalGroupMember -Group "Remote Desktop Users" -Member $Username

if ($AdminRights) {
    Add-LocalGroupMember -Group "Administrators" -Member $Username
    Write-Host "Added $Username to Administrators."
}

Write-Host "User '$Username' created."
Write-Host ""
Write-Host "For secure auto-logon, use Sysinternals Autologon.exe instead of plain registry:"
Write-Host "  https://learn.microsoft.com/sysinternals/downloads/autologon"
