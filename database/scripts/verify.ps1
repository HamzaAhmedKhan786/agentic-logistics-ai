[CmdletBinding()]
param(
    [string]$DatabaseName = 'logistics',
    [string]$AppUser = 'logistics',
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

& $psql `
    --host=$HostName `
    --port=$Port `
    --username=$AppUser `
    --dbname=$DatabaseName `
    --file="$databaseRoot\sql\verify.sql"

if ($LASTEXITCODE -ne 0) {
    throw 'PostgreSQL verification failed.'
}

Write-Host 'PostgreSQL verification completed successfully.'
