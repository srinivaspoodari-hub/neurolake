# Rust Installation Guide for NCF v2.0

**Platform**: Windows
**Required for**: Building NCF Rust implementation (v2.0)
**Performance Target**: 1.5-2M rows/sec (vs 949K rows/sec in Python v1.1)

---

## Quick Installation (Recommended)

### Option 1: Using winget (Windows 10/11)

```powershell
# Open PowerShell or Command Prompt as Administrator
winget install Rustlang.Rustup
```

**After installation**:
1. Close and reopen your terminal
2. Verify installation: `rustc --version`
3. Should see: `rustc 1.x.x (hash date)`

### Option 2: Using Official Installer

1. **Download** from: https://rustup.rs/
2. **Run** `rustup-init.exe`
3. **Follow** the installation prompts (default options are fine)
4. **Restart** your terminal

---

## Installation Steps (Detailed)

### 1. Download Rustup

Visit: https://rustup.rs/

Or direct download: https://win.rustup.rs/x86_64

### 2. Run Installer

```
rustup-init.exe
```

**You'll see**:
```
Rust Visual C++ prerequisites

Rust requires the Microsoft C++ build tools for Visual Studio 2013 or later...
```

**Options**:
- Option 1: Quick install (recommended)
- Option 2: Customize installation
- Option 3: Cancel installation

**Choose**: Option 1 (press Enter)

### 3. Accept Defaults

The installer will:
- Install Rust toolchain (rustc, cargo, rustup)
- Add to PATH automatically
- Configure default toolchain (stable)

**Wait** for download and installation (5-10 minutes)

### 4. Verify Installation

**Close and reopen** your terminal, then:

```bash
# Check Rust compiler
rustc --version

# Check Cargo (package manager)
cargo --version

# Check Rustup (toolchain manager)
rustup --version
```

**Expected output**:
```
rustc 1.75.0 (82e1608df 2023-12-21)
cargo 1.75.0 (1d8b05cdd 2023-11-20)
rustup 1.26.0 (5af9b9484 2023-04-05)
```

---

## Visual Studio Build Tools (If Needed)

If Rust installation warns about missing C++ build tools:

### Option 1: Install Build Tools Only (Lighter)

1. Download: https://visualstudio.microsoft.com/downloads/
2. Scroll to "Tools for Visual Studio"
3. Download "Build Tools for Visual Studio 2022"
4. Run installer
5. Select "Desktop development with C++"
6. Install (requires ~6 GB)

### Option 2: Install Visual Studio Community (Full IDE)

1. Download: https://visualstudio.microsoft.com/vs/community/
2. Run installer
3. Select "Desktop development with C++"
4. Install (requires ~10 GB)

**Note**: Build Tools are sufficient for NCF. Full Visual Studio is only needed if you want the IDE.

---

## Build NCF Rust Implementation

After Rust is installed:

### 1. Navigate to Project

```bash
cd C:\Users\techh\PycharmProjects\neurolake\core\ncf-rust
```

### 2. Build (Development)

```bash
# Build in debug mode (faster compilation)
cargo build

# Expected output:
#   Compiling ncf-rust v0.1.0
#   Finished dev [unoptimized + debuginfo] target(s) in 45.2s
```

### 3. Build (Release)

```bash
# Build optimized for performance
cargo build --release

# Expected output:
#   Compiling ncf-rust v0.1.0
#   Finished release [optimized] target(s) in 120.5s
```

**Binary location**: `target/release/ncf_rust.dll` (Python extension)

### 4. Run Tests

```bash
# Run all unit tests
cargo test

# Run with output
cargo test -- --nocapture

# Run specific test
cargo test test_writer_creation
```

**Expected**: 30 tests passing

### 5. Build Python Module

```bash
# Install maturin (Rust-Python build tool)
pip install maturin

# Build Python extension
maturin develop --release

# Test from Python
python -c "import ncf_rust; print('Success!')"
```

---

## Troubleshooting

### Issue 1: "rustc: command not found"

**Cause**: PATH not updated or terminal not restarted

**Solution**:
1. Close all terminals
2. Open new terminal
3. Try again
4. If still fails, check PATH manually:

```powershell
# Check PATH (PowerShell)
$env:PATH -split ';' | Select-String rust

# Should show:
# C:\Users\YourName\.cargo\bin
```

**Manual fix**:
1. Open "Environment Variables"
2. Add to PATH: `C:\Users\%USERNAME%\.cargo\bin`
3. Restart terminal

### Issue 2: "linker 'link.exe' not found"

**Cause**: Missing Visual Studio Build Tools

**Solution**: Install Build Tools (see above)

### Issue 3: Compilation errors in ncf-rust

**Check**:
```bash
cd core/ncf-rust
cargo check
```

**Common fixes**:
- Update Rust: `rustup update`
- Clean build: `cargo clean && cargo build`
- Check Cargo.toml for missing dependencies

### Issue 4: PyO3 errors

**Error**: "Could not find Python"

**Solution**:
```bash
# Set Python location
set PYO3_PYTHON=C:\Users\techh\PycharmProjects\neurolake\.venv\Scripts\python.exe

# Then build
maturin develop --release
```

### Issue 5: Slow compilation

**Normal**: First build takes 5-15 minutes (compiling dependencies)

**Speed up**:
- Subsequent builds are faster (incremental compilation)
- Use `cargo build` (debug) during development
- Only use `cargo build --release` for benchmarks

---

## Configuration

### Cargo Configuration (~/.cargo/config.toml)

Optional optimizations:

```toml
[build]
# Use all CPU cores
jobs = 8

[profile.release]
# Maximum optimization
opt-level = 3
lto = true
codegen-units = 1

[profile.dev]
# Faster debug builds
opt-level = 1
```

### Environment Variables

```bash
# Rust backtrace on errors
set RUST_BACKTRACE=1

# Verbose cargo output
set CARGO_TERM_VERBOSE=true
```

---

## Verification Checklist

After installation, verify:

- [ ] `rustc --version` works
- [ ] `cargo --version` works
- [ ] `cd core/ncf-rust && cargo build` succeeds
- [ ] `cargo test` shows 30 tests passing
- [ ] `pip install maturin` succeeds
- [ ] `maturin develop` builds Python module
- [ ] `python -c "import ncf_rust"` works

---

## Performance After Building

### Expected Improvements (vs v1.1 Python)

| Metric | v1.1 (Python) | v2.0 (Rust) | Improvement |
|--------|---------------|-------------|-------------|
| Write Speed | 949K rows/s | 1.5-2M rows/s | 1.5-2x |
| Serialization | Python loops | Zero-copy | 2-3x |
| Compression | Sequential | Parallel | 2-4x |
| Memory | +5 MB | <5 MB | Better |

### Benchmarking

After building:

```bash
# Benchmark Rust implementation
cargo bench

# Compare with Python
python tests/benchmark_rust_vs_python.py
```

---

## Quick Commands Reference

```bash
# Installation
winget install Rustlang.Rustup

# Build
cd core/ncf-rust
cargo build --release

# Test
cargo test

# Python module
pip install maturin
maturin develop --release

# Verify
python -c "import ncf_rust"

# Benchmark
cargo bench
```

---

## Resources

- **Rust Official**: https://www.rust-lang.org/
- **Rustup**: https://rustup.rs/
- **Cargo Book**: https://doc.rust-lang.org/cargo/
- **PyO3 Guide**: https://pyo3.rs/
- **Maturin**: https://maturin.rs/

---

## Next Steps After Installation

1. ✅ Install Rust
2. ✅ Build NCF Rust: `cargo build --release`
3. ✅ Run tests: `cargo test`
4. ⏳ Build Python module: `maturin develop --release`
5. ⏳ Run benchmarks: `python tests/benchmark_rust_vs_python.py`
6. ⏳ Integrate with Python NCF: Update imports

---

## Support

**Issues during installation?**

1. Check: https://doc.rust-lang.org/book/ch01-01-installation.html
2. Check: Windows-specific issues in Rust book
3. File issue: https://github.com/rust-lang/rustup/issues

**Issues with NCF Rust build?**

1. Run: `cargo check` for detailed errors
2. Check: `Cargo.toml` dependencies
3. Verify: PyO3 configuration

---

*Last Updated*: October 31, 2025
*Platform*: Windows
*Estimated Time*: 10-30 minutes (including downloads)
