# NCF v2.0 Build and Test Script
# Run this AFTER installing Visual Studio C++ Build Tools workload

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "NCF v2.0 Rust - Build and Test Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if C++ compiler is available
Write-Host "[1/7] Checking C++ compiler..." -ForegroundColor Yellow
$clPath = Get-Command cl.exe -ErrorAction SilentlyContinue
if ($null -eq $clPath) {
    Write-Host "ERROR: cl.exe not found!" -ForegroundColor Red
    Write-Host "Please install Visual Studio C++ Build Tools workload first." -ForegroundColor Red
    Write-Host "See INSTALLATION_REQUIRED.md for instructions." -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Found: $($clPath.Source)" -ForegroundColor Green
Write-Host ""

# Step 1: Build Rust NCF
Write-Host "[2/7] Building Rust NCF (release mode)..." -ForegroundColor Yellow
Write-Host "  This will take 5-10 minutes on first build..." -ForegroundColor Gray
Push-Location "$PSScriptRoot\core\ncf-rust"
try {
    & "C:\Users\techh\.cargo\bin\cargo.exe" build --release
    if ($LASTEXITCODE -ne 0) {
        throw "Cargo build failed with exit code $LASTEXITCODE"
    }
    Write-Host "  ✓ Build successful!" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Build failed: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host ""

# Step 2: Run Rust unit tests
Write-Host "[3/7] Running Rust unit tests..." -ForegroundColor Yellow
try {
    & "C:\Users\techh\.cargo\bin\cargo.exe" test --release
    if ($LASTEXITCODE -ne 0) {
        throw "Cargo test failed with exit code $LASTEXITCODE"
    }
    Write-Host "  ✓ All Rust tests passed!" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Tests failed: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host ""

# Step 3: Install Python requirements
Write-Host "[4/7] Installing Python requirements..." -ForegroundColor Yellow
Push-Location "$PSScriptRoot"
& ".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
& ".venv\Scripts\pip.exe" install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠ Some requirements failed, continuing..." -ForegroundColor Yellow
} else {
    Write-Host "  ✓ Requirements installed!" -ForegroundColor Green
}
Write-Host ""

# Step 4: Install maturin
Write-Host "[5/7] Installing maturin..." -ForegroundColor Yellow
& ".venv\Scripts\pip.exe" install maturin
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Maturin installed!" -ForegroundColor Green
} else {
    Write-Host "  ✗ Maturin installation failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host ""

# Step 5: Build Python extension
Write-Host "[6/7] Building Python extension with maturin..." -ForegroundColor Yellow
Push-Location "$PSScriptRoot\core\ncf-rust"
& "..\..\..venv\Scripts\maturin.exe" develop --release
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Python extension built!" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python extension build failed" -ForegroundColor Red
    Pop-Location
    Pop-Location
    exit 1
}
Pop-Location
Write-Host ""

# Step 6: Test Python import
Write-Host "[7/7] Testing Python import..." -ForegroundColor Yellow
& ".venv\Scripts\python.exe" -c "import ncf_rust; print('✓ NCF v2.0 Rust module loaded successfully!')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Import failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host ""

Pop-Location

# Success!
Write-Host "============================================================" -ForegroundColor Green
Write-Host "SUCCESS! NCF v2.0 built successfully!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run integration tests:" -ForegroundColor White
Write-Host "     .venv\Scripts\python.exe -m pytest tests\test_rust_integration.py -v" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Run benchmarks:" -ForegroundColor White
Write-Host "     .venv\Scripts\python.exe tests\benchmark_rust_vs_python.py" -ForegroundColor Gray
Write-Host ""
Write-Host "Expected performance:" -ForegroundColor Cyan
Write-Host "  • Python v1.1:  949,000 rows/sec" -ForegroundColor Gray
Write-Host "  • Rust v2.0:    1,500,000 - 2,000,000 rows/sec (1.5-2x faster!)" -ForegroundColor Gray
Write-Host "  • Parquet:      1,670,000 rows/sec" -ForegroundColor Gray
Write-Host ""
Write-Host "Goal: Match or beat Parquet! 🎯" -ForegroundColor Yellow
Write-Host ""
