# Resolve the Python entry point when sourced, not from the caller's directory.
$script:StartTmuxScript = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'starttmux.py'

function starttmux {
    if (Get-Command py -CommandType Application -ErrorAction SilentlyContinue) {
        & py -3 $script:StartTmuxScript @args
    } elseif (Get-Command python -CommandType Application -ErrorAction SilentlyContinue) {
        & python $script:StartTmuxScript @args
    } else {
        $global:LASTEXITCODE = 1
        Write-Error 'starttmux requires Python 3.8 or newer. Install Python and add it to PATH.'
        return
    }
    $global:LASTEXITCODE = $LASTEXITCODE
}
