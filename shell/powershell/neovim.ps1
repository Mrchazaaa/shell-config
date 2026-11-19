$env:EDITOR = 'nvim'

function nvim-code {
    $previous = $env:NVIM_APPNAME
    try {
        $env:NVIM_APPNAME = 'nvim'
        & nvim @args
    } finally {
        $env:NVIM_APPNAME = $previous
    }
}

function nvim-hemingway {
    $previous = $env:NVIM_APPNAME
    try {
        $env:NVIM_APPNAME = 'nvim/vim-config/profiles/hemingway'
        & nvim @args
    } finally {
        $env:NVIM_APPNAME = $previous
    }
}

function nvim-clean { & nvim --clean @args }
