# Test OriginX Deployment
Write-Host "Testing OriginX Deployment on port 8000..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Health endpoint
Write-Host "1. Testing /api/health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get
    Write-Host "   ✓ Health check passed" -ForegroundColor Green
    Write-Host "   Status: $($health.status)" -ForegroundColor Gray
    Write-Host "   Platform: $($health.platform)" -ForegroundColor Gray
    Write-Host "   Version: $($health.version)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Health check failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 2: Frontend root
Write-Host "2. Testing frontend root (/)..." -ForegroundColor Yellow
try {
    $root = Invoke-WebRequest -Uri "http://localhost:8000/" -Method Get
    Write-Host "   ✓ Frontend root accessible" -ForegroundColor Green
    Write-Host "   Status: $($root.StatusCode)" -ForegroundColor Gray
    Write-Host "   Content-Type: $($root.Headers.'Content-Type')" -ForegroundColor Gray
    Write-Host "   Content Length: $($root.Content.Length) bytes" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Frontend root failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 3: Registry endpoint
Write-Host "3. Testing /api/consent/registry..." -ForegroundColor Yellow
try {
    $registry = Invoke-RestMethod -Uri "http://localhost:8000/api/consent/registry" -Method Get
    Write-Host "   ✓ Registry API working" -ForegroundColor Green
    Write-Host "   Total users: $($registry.total)" -ForegroundColor Gray
    Write-Host "   Records: $($registry.records.Count)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Registry API failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 4: Static assets
Write-Host "4. Testing static assets (/assets/)..." -ForegroundColor Yellow
try {
    $assets = Invoke-WebRequest -Uri "http://localhost:8000/assets/index-BiBOy0bu.js" -Method Get -ErrorAction Stop
    Write-Host "   ✓ Static assets accessible" -ForegroundColor Green
    Write-Host "   Status: $($assets.StatusCode)" -ForegroundColor Gray
    Write-Host "   Content Length: $($assets.Content.Length) bytes" -ForegroundColor Gray
} catch {
    Write-Host "   ⚠ Static assets test: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Deployment test complete!" -ForegroundColor Cyan
