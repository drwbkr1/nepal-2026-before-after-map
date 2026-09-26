param([switch]$CheckRelease, [switch]$UseExistingToken)

$ErrorActionPreference = 'Stop'
$probe = Join-Path $PSScriptRoot 'm2_asf_hyp3_account_probe_001.py'
$pythonCommand = Get-Command python -ErrorAction Stop
$pythonPath = $pythonCommand.Source

# This child checks public CI, scoped source rights, and final no-content
# preflight before PowerShell asks for any secret.
$gateOutput = & $pythonPath $probe --check-release
if ($LASTEXITCODE -ne 0) {
    Write-Output 'HyP3 account handoff is not released; no token was requested.'
    exit 12
}
try {
    $gate = $gateOutput | ConvertFrom-Json -ErrorAction Stop
    if ($gate.status -ne 'pass_account_probe_release_no_secret_read') {
        throw 'gate mismatch'
    }
} catch {
    Write-Output 'HyP3 account handoff gate could not be verified; no token was requested.'
    exit 12
}
if ($CheckRelease) {
    Write-Output 'HyP3 account probe released; no token was requested.'
    exit 0
}

$bstr = [IntPtr]::Zero
$secureToken = $null
$securePassword = $null
$passwordBstr = [IntPtr]::Zero
$password = $null
$username = $null
$token = $null
$child = $null
try {
    if ($UseExistingToken) {
        $secureToken = Read-Host 'NASA Earthdata bearer token (hidden; paste once)' -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
        $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    } else {
        Write-Output 'Earthdata may create a 60-day user token if none exists; it will not be printed or saved.'
        $choice = Read-Host 'Continue with your Earthdata username and password? [y/N]'
        if ($choice -notin @('y', 'Y')) {
            Write-Output 'HyP3 account handoff cancelled; no credentials were requested.'
            exit 0
        }
        $username = Read-Host 'NASA Earthdata username'
        $securePassword = Read-Host 'NASA Earthdata password (hidden)' -AsSecureString
        $passwordBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
        $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordBstr)
        if ([string]::IsNullOrWhiteSpace($username) -or [string]::IsNullOrEmpty($password) -or $username.Contains(':') -or $username.Contains("`n") -or $password.Contains("`n")) {
            throw 'invalid credentials shape'
        }
    }
    if ($UseExistingToken) {
        if ([string]::IsNullOrWhiteSpace($token) -or $token.Length -gt 4096 -or $token -cnotmatch '^[A-Za-z0-9._-]+$') {
            throw 'invalid token shape'
        }
    }
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $pythonPath
    if ($UseExistingToken) {
        $start.Arguments = ('"{0}"' -f $probe)
    } else {
        $start.Arguments = ('"{0}" --earthdata-credentials' -f $probe)
    }
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $child = New-Object System.Diagnostics.Process
    $child.StartInfo = $start
    if (-not $child.Start()) {
        throw 'child launch failed'
    }
    if ($UseExistingToken) {
        $child.StandardInput.WriteLine($token)
    } else {
        $child.StandardInput.WriteLine($username)
        $child.StandardInput.WriteLine($password)
    }
    $child.StandardInput.Close()
    $token = $null
    $username = $null
    $password = $null
    $resultText = $child.StandardOutput.ReadToEnd()
    $null = $child.StandardError.ReadToEnd()
    $child.WaitForExit()
    $result = $resultText | ConvertFrom-Json -ErrorAction Stop
    if ($child.ExitCode -ne 0 -or $result.status -ne 'account_probe_pass_free_credit_capacity_only') {
        Write-Output ('HyP3 account probe stopped: {0}' -f $result.code)
        exit 12
    }
    # The Python child emits only a yes/no free-capacity result.
    Write-Output $resultText.Trim()
} catch {
    Write-Output 'Secret-safe HyP3 account handoff stopped without a verified result. Earthdata may have created or returned a token; check your Earthdata token page if needed.'
    exit 20
} finally {
    $token = $null
    $secureToken = $null
    $securePassword = $null
    $password = $null
    $username = $null
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    if ($passwordBstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordBstr)
    }
    if ($null -ne $child) {
        $child.Dispose()
    }
}
