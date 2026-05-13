# Installs a virtual display driver so the agent session always has a monitor.
# Recommended: IddSampleDriver (Microsoft reference indirect display driver).
#
# Options:
#   IddSampleDriver: https://github.com/itsmikethetech/Virtual-Display-Driver
#   usbmmidd_v2:     https://github.com/ccrisan/usbmmidd
#   Parsec Virtual Display Adapter: installed automatically with Parsec

param(
    [ValidateSet("idd", "usbmmidd", "parsec")]
    [string]$Driver = "idd",
    [int]$Width = 1920,
    [int]$Height = 1080
)

Write-Host "Virtual display driver: $Driver"
Write-Host "Requested resolution: ${Width}x${Height}"
Write-Host ""

switch ($Driver) {
    "idd" {
        Write-Host "Download IddSampleDriver from:"
        Write-Host "  https://github.com/itsmikethetech/Virtual-Display-Driver/releases"
        Write-Host "Run the installer as Administrator, then reboot."
    }
    "usbmmidd" {
        Write-Host "Download usbmmidd_v2 from:"
        Write-Host "  https://github.com/ccrisan/usbmmidd/releases"
        Write-Host "Run: deviceinstaller64 install usbmmidd.inf usbmmidd"
    }
    "parsec" {
        Write-Host "Install Parsec — the virtual display adapter is included."
        Write-Host "No Parsec subscription required for local use."
    }
}

Write-Host ""
Write-Host "After reboot, confirm the virtual monitor appears in Display Settings."
Write-Host "Set it as default in the agent session: DisplaySwitch.exe /internal"
