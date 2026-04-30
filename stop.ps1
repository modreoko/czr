# Stop uvicorn + pipeline processes started by start.ps1 and stop Docker Compose.
$root = $PSScriptRoot

$pidFiles = @{
    'uvicorn.pid' = 'uvicorn'
    'pipeline.pid' = 'pipeline'
}

foreach ($file in $pidFiles.Keys) {
    $path = Join-Path $root $file
    if (Test-Path $path) {
        $pid = Get-Content $path | ForEach-Object { $_.Trim() } | Where-Object { $_ -match '^[0-9]+$' }
        if ($pid) {
            Write-Host "Stopping $($pidFiles[$file]) process PID $pid..."
            Stop-Process -Id $pid -ErrorAction SilentlyContinue
        }
        Remove-Item $path -ErrorAction SilentlyContinue
    }
}

Write-Host "Stopping Docker Compose services..."
docker-compose down

Write-Host "Stopped."