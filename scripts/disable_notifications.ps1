# Suppress Windows notifications and focus-stealing events in the agent session.
# Run as the 'agent' user (not Administrator) so HKCU targets the right profile.

# Toast notifications
$pushPath = 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\PushNotifications'
if (-not (Test-Path $pushPath)) { New-Item -Force -Path $pushPath | Out-Null }
Set-ItemProperty -Path $pushPath -Name ToastEnabled -Value 0

# Focus Assist
$faPath = 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\CloudStore\Store\Cache\DefaultAccount'
if (Test-Path $faPath) {
    Set-ItemProperty -Path $faPath -Name Current -Value 2 -ErrorAction SilentlyContinue
}

# Windows Update reboot nag (requires admin — run once as admin for the machine)
$wuPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU'
if (-not (Test-Path $wuPath)) { New-Item -Force -Path $wuPath | Out-Null }
Set-ItemProperty -Path $wuPath -Name NoAutoRebootWithLoggedOnUsers -Value 1

# Game Bar
$gbPath = 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR'
if (-not (Test-Path $gbPath)) { New-Item -Force -Path $gbPath | Out-Null }
Set-ItemProperty -Path $gbPath -Name AppCaptureEnabled -Value 0
Set-ItemProperty -Path 'HKCU:\System\GameConfigStore' -Name GameDVR_Enabled -Value 0 -ErrorAction SilentlyContinue

# Action Center / Notification Center
$acPath = 'HKCU:\SOFTWARE\Policies\Microsoft\Windows\Explorer'
if (-not (Test-Path $acPath)) { New-Item -Force -Path $acPath | Out-Null }
Set-ItemProperty -Path $acPath -Name DisableNotificationCenter -Value 1

Write-Host "Notifications suppressed for current user ($env:USERNAME)."
