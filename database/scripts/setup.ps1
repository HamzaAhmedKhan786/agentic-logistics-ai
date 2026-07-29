[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z_][A-Za-z0-9_]*$')]
    [string]$DatabaseName = 'logistics',

    [ValidatePattern('^[A-Za-z_][A-Za-z0-9_]*$')]
    [string]$AppUser = 'logistics',

    [string]$AdminUser = 'postgres',
    [string]$HostName = 'localhost',

    [ValidateRange(1, 65535)]
    [int]$Port = 5432
)

$ErrorActionPreference = 'Stop'
$databaseRoot = Split-Path -Parent $PSScriptRoot

function Find-Psql {
    $command = Get-Command psql.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $postgresRoot = 'C:\Program Files\PostgreSQL'
    if (Test-Path -LiteralPath $postgresRoot) {
        $installations = Get-ChildItem -LiteralPath $postgresRoot -Directory |
            Where-Object { $_.Name -match '^\d+' } |
            Sort-Object { [int]([regex]::Match($_.Name, '^\d+').Value) } -Descending
        foreach ($installation in $installations) {
            $candidate = Join-Path $installation.FullName 'bin\psql.exe'
            if (Test-Path -LiteralPath $candidate) {
                return $candidate
            }
        }
    }

    throw 'psql.exe was not found in PATH or a standard PostgreSQL installation.'
}

$psql = Find-Psql
Write-Host "Using PostgreSQL client: $psql"

$securePassword = Read-Host "Password for application role '$AppUser'" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)

try {
    $appPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)

    Write-Host "Creating/updating role '$AppUser' and database '$DatabaseName'..."
    & $psql `
        --host=$HostName `
        --port=$Port `
        --username=$AdminUser `
        --dbname=postgres `
        --set=app_user=$AppUser `
        --set=app_password=$appPassword `
        --set=db_name=$DatabaseName `
        --file="$databaseRoot\sql\001_create_database.sql"

    if ($LASTEXITCODE -ne 0) {
        throw 'Database or role creation failed.'
    }

    $previousPassword = $env:PGPASSWORD
    $env:PGPASSWORD = $appPassword
    try {
        Write-Host 'Applying application schema...'
        & $psql `
            --host=$HostName `
            --port=$Port `
            --username=$AppUser `
            --dbname=$DatabaseName `
            --file="$databaseRoot\sql\002_schema.sql"

        if ($LASTEXITCODE -ne 0) {
            throw 'Schema creation failed.'
        }

        & $psql `
            --host=$HostName `
            --port=$Port `
            --username=$AppUser `
            --dbname=$DatabaseName `
            --file="$databaseRoot\sql\003_updated_at_trigger.sql"

        if ($LASTEXITCODE -ne 0) {
            throw 'Trigger creation failed.'
        }
    }
    finally {
        $env:PGPASSWORD = $previousPassword
    }

    $encodedPassword = [Uri]::EscapeDataString($appPassword)
    Write-Host ''
    Write-Host 'PostgreSQL setup completed.'
    Write-Host 'Add this value to your .env file:'
    Write-Host "DATABASE_URL=postgresql+asyncpg://${AppUser}:${encodedPassword}@${HostName}:${Port}/${DatabaseName}"
}
finally {
    if ($passwordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
    Remove-Variable appPassword -ErrorAction SilentlyContinue
}
