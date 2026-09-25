[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$projectRoot = Split-Path -Parent $PSScriptRoot
$gatePath = Join-Path $projectRoot 'records\readiness\m2-optical-pair-pilot-001-execution-gate-002.json'
$brokerPath = Join-Path $PSScriptRoot 'm2_optical_pair_pilot_001_broker.py'
$tokenEndpoint = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
$passwordBstr = [IntPtr]::Zero
$totpBstr = [IntPtr]::Zero
$plainPassword = $null
$plainTotp = $null
$tokenResponse = $null
$accessToken = $null

try {
    if (-not (Test-Path -LiteralPath $gatePath -PathType Leaf)) {
        throw 'pilot_execution_gate_missing'
    }
    $gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
    if ($gate.status -ne 'pass_public_execution_gate' -or $gate.public_ci_conclusion -ne 'success') {
        throw 'pilot_execution_gate_not_passing'
    }
    $username = Read-Host 'CDSE username (normally your account email)'
    if ([string]::IsNullOrWhiteSpace($username)) {
        throw 'missing_username'
    }
    $securePassword = Read-Host 'CDSE password' -AsSecureString
    $secureTotp = Read-Host 'Current CDSE 2FA code, or press Enter if 2FA is disabled' -AsSecureString
    $passwordBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordBstr)
    $totpBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureTotp)
    $plainTotp = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($totpBstr)
    $body = @{
        client_id = 'cdse-public'
        grant_type = 'password'
        username = $username
        password = $plainPassword
    }
    if (-not [string]::IsNullOrWhiteSpace($plainTotp)) {
        $body['totp'] = $plainTotp
    }
    try {
        $tokenResponse = Invoke-RestMethod -Method Post -Uri $tokenEndpoint -ContentType 'application/x-www-form-urlencoded' -Body $body
    }
    catch {
        throw 'cdse_token_request_failed'
    }
    $accessToken = [string]$tokenResponse.access_token
    if ([string]::IsNullOrWhiteSpace($accessToken) -or $accessToken -match '\s') {
        throw 'cdse_token_response_invalid'
    }
    $accessToken | & python $brokerPath
    if ($LASTEXITCODE -ne 0) {
        throw 'pilot_broker_handoff_failed'
    }
}
catch {
    Write-Error ('Secret-safe optical pilot stopped: {0}' -f $_.Exception.Message)
    exit 12
}
finally {
    $accessToken = $null
    $tokenResponse = $null
    $body = $null
    $plainPassword = $null
    $plainTotp = $null
    if ($passwordBstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordBstr)
    }
    if ($totpBstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($totpBstr)
    }
}
