# Enables WinRM and PowerShell Remoting on the target machine.
# Backup remote-management channel when SSH is unavailable.
# Run as Administrator.
#
# Usage from dev machine:
#   Enter-PSSession -ComputerName <ip> -Credential agent

param(
    [string]$TrustedHost = "*"   # narrow this to your dev machine IP in production
)

# Enable PSRemoting (starts WinRM, creates listener, adds firewall rule)
Enable-PSRemoting -Force

# Trust the dev machine (or all hosts for initial setup)
Set-Item WSMan:\localhost\Client\TrustedHosts -Value $TrustedHost -Force

# Increase max envelope size for large responses (UIA tree dumps can be big)
Set-Item WSMan:\localhost\Shell\MaxMemoryPerShellMB -Value 1024

# Confirm
Write-Host "WinRM enabled. TrustedHosts: $TrustedHost"
Write-Host "Test from dev machine:"
Write-Host "  Test-WSMan -ComputerName <ip>"
Write-Host "  Enter-PSSession -ComputerName <ip> -Credential agent"
