# Run in the PowerShell edition whose profile should load this configuration.
& {
    $ErrorActionPreference = 'Stop'
    $repository = 'https://github.com/Mrchazaaa/shell-config.git'
    $destination = Join-Path $HOME '.config/shell-config'
    $loader = '. (Join-Path $HOME ''.config/shell-config/init.ps1'')'

    if (-not (Get-Command git -CommandType Application -ErrorAction SilentlyContinue)) {
        throw 'git is required. Install it and run this installer again.'
    }

    if (Test-Path -LiteralPath $destination) {
        if (-not (Test-Path -LiteralPath (Join-Path $destination '.git') -PathType Container)) {
            throw "$destination already exists and is not the expected shell-config checkout."
        }
        $origin = & git -C $destination remote get-url origin
        if ($LASTEXITCODE -ne 0 -or $origin -ne $repository -or
            -not (Test-Path -LiteralPath (Join-Path $destination 'init.ps1') -PathType Leaf)) {
            throw "$destination already exists and is not the expected shell-config checkout."
        }
        Write-Host "Using existing checkout at $destination"
    } else {
        New-Item -ItemType Directory -Path (Split-Path $destination) -Force | Out-Null
        & git clone $repository $destination
        if ($LASTEXITCODE -ne 0) { throw 'Could not clone shell-config.' }
    }

    $lines = if (Test-Path -LiteralPath $PROFILE) { @(Get-Content -LiteralPath $PROFILE) } else { @() }
    if ($lines -cnotcontains $loader) {
        New-Item -ItemType Directory -Path (Split-Path $PROFILE) -Force | Out-Null
        Add-Content -LiteralPath $PROFILE -Value "`n$loader" -Encoding utf8
        Write-Host "Added shell-config to $PROFILE"
    } else {
        Write-Host "shell-config is already configured in $PROFILE"
    }
    Write-Host 'Installation complete. Open a new PowerShell session or run: . $PROFILE'
}
