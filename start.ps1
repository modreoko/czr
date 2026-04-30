# Activate virtual environment (for shell commands)
& ".\.venv\Scripts\Activate.ps1"

# Path to venv python
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Python venv not found at $python. Run 'python -m venv .venv' first."
    exit 1
}

# Ensure uvicorn is installed in the venv
$uvicornInstalled = & $python -m pip show uvicorn 2>$null
if (-not $uvicornInstalled) {
    Write-Host "uvicorn is not installed. Installing uvicorn[standard]..."
    & $python -m pip install "uvicorn[standard]"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "uvicorn installation failed. Check pip and try again."
        exit 1
    }
}

# Start Docker services
Write-Host "Starting Docker Compose..."
docker-compose up -d

# Wait for Ollama and Qdrant to become available
Write-Host "Waiting for Ollama to become available on localhost:11434..."
$ollamaMaxRetries = 15
$ollamaRetry = 0
while ($ollamaRetry -lt $ollamaMaxRetries) {
    $conn = Test-NetConnection -ComputerName "localhost" -Port 11434
    if ($conn.TcpTestSucceeded) {
        Write-Host "Ollama is available."
        break
    }
    Start-Sleep -Seconds 2
    $ollamaRetry++
}
if ($ollamaRetry -ge $ollamaMaxRetries) {
    Write-Error "Ollama did not start in time. Please check Docker and try again."
    exit 1
}

function Test-OllamaModel($model) {
    $result = docker exec ollama ollama list 2>$null | Select-String -Pattern ([regex]::Escape($model))
    return $result -ne $null
}

function Pull-OllamaModel($model) {
    Write-Host "Pulling Ollama model $model into the container..."
    docker exec ollama ollama pull $model
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to pull Ollama model $model."
        exit 1
    }
}

$embedModel = 'nomic-embed-text:latest'
$chatModel = 'qwen2.5:7b'

if (-not (Test-OllamaModel $embedModel)) {
    Pull-OllamaModel $embedModel
}
if (-not (Test-OllamaModel $chatModel)) {
    Pull-OllamaModel $chatModel
}

# Load models into memory by making a test API call
Write-Host "Loading models into Ollama memory..."
try {
    $testResponse = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body '{"model":"nomic-embed-text:latest","prompt":"test","stream":false}' -ContentType "application/json" -TimeoutSec 30
} catch {
    Write-Host "Warning: Could not load embedding model, but continuing..."
}
try {
    $testResponse = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body ('{"model":"' + $chatModel + '","prompt":"test","stream":false}') -ContentType "application/json" -TimeoutSec 30
} catch {
    Write-Host "Warning: Could not load chat model, but continuing..."
}

# Wait for Qdrant to become available
Write-Host "Waiting for Qdrant to become available on localhost:6333..."
$maxRetries = 15
$retry = 0
while ($retry -lt $maxRetries) {
    $conn = Test-NetConnection -ComputerName "localhost" -Port 6333
    if ($conn.TcpTestSucceeded) {
        Write-Host "Qdrant is ready."
        break
    }
    Start-Sleep -Seconds 2
    $retry++
}
if ($retry -ge $maxRetries) {
    Write-Error "Qdrant did not start in time. Please check Docker and try again."
    exit 1
}

# Start ingestion pipeline in background process
Write-Host "Starting ingest pipeline..."
$p1 = Start-Process -FilePath $python -ArgumentList '-m', 'ingest.pipeline' -WindowStyle Hidden -PassThru
$p1.Id | Out-File -FilePath (Join-Path $PSScriptRoot 'pipeline.pid') -Encoding ascii

# Start FastAPI server in background process with reload
Write-Host "Starting uvicorn server..."
$p2 = Start-Process -FilePath $python -ArgumentList '-m', 'uvicorn', 'api.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000' -WindowStyle Hidden -PassThru
$p2.Id | Out-File -FilePath (Join-Path $PSScriptRoot 'uvicorn.pid') -Encoding ascii

# Wait for API to start
Start-Sleep -Seconds 5

# Open browser
Start-Process "http://localhost:8000"

Write-Host "Application started."
Write-Host "Pipeline PID: $($p1.Id), Uvicorn PID: $($p2.Id)"
Write-Host "If you want to stop everything, run stop.ps1 or docker-compose down."