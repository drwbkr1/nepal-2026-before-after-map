param([switch]$CheckRelease, [switch]$UseExistingToken)

$ErrorActionPreference = 'Stop'
$worker = Join-Path $PSScriptRoot 'm2_asf_hyp3_rtc_submit_first_001.py'
$pythonPath = (Get-Command python -ErrorAction Stop).Source

# Check every published gate before asking for a secret.
$gateOutput = & $pythonPath $worker --check-release
if ($LASTEXITCODE -ne 0) {
    Write-Output 'HyP3 first RTC submission is not released; no credential was requested.'
    exit 12
}
try {
    $gate = $gateOutput | ConvertFrom-Json -ErrorAction Stop
    if ($gate.status -ne 'pass_submit_first_release_no_secret_read') { throw 'gate mismatch' }
} catch {
    Write-Output 'HyP3 first RTC gate could not be verified; no credential was requested.'
    exit 12
}
if ($CheckRelease) {
    Write-Output 'HyP3 first RTC submission released; no credential was requested.'
    exit 0
}

$bstr = [IntPtr]::Zero
$passwordBstr = [IntPtr]::Zero
$secureToken = $null
$securePassword = $null
$token = $null
$username = $null
$password = $null
$child = $null
try {
    if ($UseExistingToken) {
        $secureToken = Read-Host 'NASA Earthdata bearer token (hidden; paste once)' -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
        $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        if ([string]::IsNullOrWhiteSpace($token) -or $token.Length -gt 4096 -or $token -cnotmatch '^[A-Za-z0-9._-]+$') {
            throw 'invalid token shape'
        }
    } else {
        Write-Output 'Earthdata may create a 60-day user token if none exists; it will not be printed or saved.'
        $choice = Read-Host 'Continue with your Earthdata username and password? [y/N]'
        if ($choice -notin @('y', 'Y')) {
            Write-Output 'HyP3 submission cancelled; no credentials were requested.'
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

    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $pythonPath
    $start.Arguments = if ($UseExistingToken) { ('"{0}"' -f $worker) } else { ('"{0}" --earthdata-credentials' -f $worker) }
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $child = New-Object System.Diagnostics.Process
    $child.StartInfo = $start
    if (-not $child.Start()) { throw 'child launch failed' }
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
    if ($child.ExitCode -ne 0) {
        Write-Output ('HyP3 first RTC submission stopped: {0}' -f $result.code)
        exit 12
    }
    if ($result.status -ne 'submitted_product_unverified') { throw 'result mismatch' }
    Write-Output $resultText.Trim()
} catch {
    Write-Output 'Secret-safe HyP3 submission stopped without a verified result. Inspect the non-Git attempt receipts; do not retry.'
    exit 20
} finally {
    $token = $null
    $username = $null
    $password = $null
    $secureToken = $null
    $securePassword = $null
    if ($bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    if ($passwordBstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordBstr) }
    if ($null -ne $child) { $child.Dispose() }
}
