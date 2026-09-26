param([switch]$CheckRelease)

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

$secureToken = Read-Host 'NASA Earthdata bearer token (hidden; paste once)' -AsSecureString
$bstr = [IntPtr]::Zero
$token = $null
$child = $null
try {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    if ([string]::IsNullOrWhiteSpace($token)) {
        throw 'empty token'
    }
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $pythonPath
    $start.Arguments = ('"{0}"' -f $probe)
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
    $child.StandardInput.WriteLine($token)
    $child.StandardInput.Close()
    $token = $null
    $resultText = $child.StandardOutput.ReadToEnd()
    $null = $child.StandardError.ReadToEnd()
    $child.WaitForExit()
    $result = $resultText | ConvertFrom-Json -ErrorAction Stop
    if ($child.ExitCode -ne 0 -or $result.status -ne 'account_probe_pass_free_credit_capacity_only') {
        Write-Output ('HyP3 account probe stopped: {0}' -f $result.code)
        exit 12
    }
    # The Python child emits only balance and non-identifying status.
    Write-Output $resultText.Trim()
} catch {
    Write-Output 'Secret-safe HyP3 account handoff stopped before a verified account result.'
    exit 20
} finally {
    $token = $null
    $secureToken = $null
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    if ($null -ne $child) {
        $child.Dispose()
    }
}
