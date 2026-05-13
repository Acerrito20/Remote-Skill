# Installs and configures the built-in Windows OpenSSH server.
# Run as Administrator.
#
# After this script:
#   - SSH listens on port 22 with key-based auth only
#   - Default shell is PowerShell
#   - Firewall rule is created

param(
    [string]$AuthorizedKey = "",   # paste your public key here, or set afterward
    [string]$AgentUser = "agent"
)

# Install the OpenSSH server capability
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Start and set to automatic
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

# Firewall rule
if (-not (Get-NetFirewallRule -Name sshd -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
}

# Disable password auth, enable key auth
$sshdConfig = "C:\ProgramData\ssh\sshd_config"
(Get-Content $sshdConfig) `
    -replace '#PubkeyAuthentication yes', 'PubkeyAuthentication yes' `
    -replace 'PasswordAuthentication yes', 'PasswordAuthentication no' `
    | Set-Content $sshdConfig

# Set PowerShell as default shell
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell `
    -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -PropertyType String -Force

# Provision authorized_keys if a key was provided
if ($AuthorizedKey) {
    $sshDir = "C:\Users\$AgentUser\.ssh"
    New-Item -ItemType Directory -Force -Path $sshDir | Out-Null
    $AuthorizedKey | Set-Content "$sshDir\authorized_keys" -Encoding UTF8

    # Fix ACLs — Windows is strict about authorized_keys permissions
    icacls "$sshDir\authorized_keys" /inheritance:r /grant "${AgentUser}:F" /grant "SYSTEM:F"
}

Restart-Service sshd
Write-Host "OpenSSH server installed. Test with: ssh ${AgentUser}@localhost"
Write-Host "Add ~/.ssh/config entry on your dev machine:"
Write-Host "  Host cdg-agent"
Write-Host "    HostName <this-machine-ip>"
Write-Host "    User $AgentUser"
Write-Host "    IdentityFile ~/.ssh/id_ed25519"
