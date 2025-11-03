# Visual Studio Build Tools Setup (REQUIRED)

**Date**: November 1, 2025
**Status**: Base installer installed, C++ workload needed
**Time Required**: 10-15 minutes

---

## Why This Is Needed

Both **Rust** and **Python's numpy** require the Microsoft C++ compiler and linker (`link.exe`) to build native code on Windows. Without this:

- ❌ Rust build fails: "linking with `link.exe` failed"
- ❌ numpy install fails: "Unknown compiler(s): [['cl'], ['gcc']]"
- ❌ NCF v2.0 cannot be built

---

## Current Status

✅ **Visual Studio Build Tools 2022 base installer** - Installed
❌ **Desktop development with C++ workload** - Missing (required)

---

## Step 1: Open Visual Studio Installer

**Option A: Using Start Menu**
1. Press Windows key
2. Type "Visual Studio Installer"
3. Click to open

**Option B: Using File Explorer**
1. Navigate to: `C:\Program Files (x86)\Microsoft Visual Studio\Installer`
2. Double-click `vs_installer.exe`

---

## Step 2: Modify Installation

1. In the Visual Studio Installer window, you'll see:
   ```
   Visual Studio Build Tools 2022
   [Modify] [More ▼]
   ```

2. Click the **[Modify]** button

3. In the **Workloads** tab, find and check:
   ```
   ☑ Desktop development with C++
   ```

4. On the right panel, verify these are checked:
   - ☑ MSVC v143 - VS 2022 C++ x64/x86 build tools
   - ☑ Windows 11 SDK (or Windows 10 SDK)
   - ☑ C++ CMake tools for Windows

5. Click **[Modify]** button at bottom right

6. Wait for installation (5-10 minutes)
   - This will download ~6-8 GB of tools
   - Progress will be shown in the installer

---

## Step 3: Verify Installation

After installation completes, open a **NEW terminal** (important!) and run:

```powershell
# Verify C++ compiler is available
where cl

# Expected output:
# C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.xx\bin\Hostx64\x64\cl.exe
```

If you see the path to `cl.exe`, the installation was successful!

---

## Step 4: Build NCF Rust Implementation

Once the C++ tools are installed, navigate back to the neurolake project and build:

```bash
cd C:\Users\techh\PycharmProjects\neurolake\core\ncf-rust

# Build Rust NCF (should work now!)
cargo build --release

# Run tests (30 tests should pass)
cargo test

# Expected output:
# test result: ok. 30 passed; 0 failed
```

---

## Step 5: Install Python Dependencies (in venv)

With the C++ compiler installed, numpy can now be built:

```bash
cd C:\Users\techh\PycharmProjects\neurolake

# Activate venv
.venv\Scripts\activate

# Install requirements (numpy will build successfully now)
pip install -r requirements.txt

# This should now work:
# - pyspark
# - numpy 1.26.4 (will compile from source)
# - delta-spark
# - pyarrow
```

---

## Troubleshooting

### Issue: "cl.exe not found" after installation

**Solution**: Close ALL terminals and VS Code, then reopen. The PATH needs to be refreshed.

### Issue: Installer says "Another installation in progress"

**Solution**:
1. Open Task Manager (Ctrl+Shift+Esc)
2. End any `vs_installer.exe` or `setup.exe` processes
3. Retry

### Issue: Not enough disk space

**Solution**:
- C++ Build Tools require ~8 GB free space
- Clear temporary files or free up space on C: drive

### Issue: Installation fails with error code

**Solution**:
1. Check Windows Updates are current
2. Restart computer
3. Run installer as Administrator
4. If still fails, download offline installer from:
   https://visualstudio.microsoft.com/downloads/

---

## What Gets Installed

The "Desktop development with C++" workload includes:

| Component | Purpose | Size |
|-----------|---------|------|
| MSVC Compiler (`cl.exe`) | Compiles C++ code | ~1 GB |
| Windows SDK | Windows headers & libraries | ~2 GB |
| CMake | Build system | ~100 MB |
| Link.exe | Linker for executables | ~50 MB |
| Other tools | Debuggers, analyzers | ~3 GB |

**Total**: ~6-8 GB

---

## Alternative: Use Rust's GNU Toolchain (Not Recommended)

If you can't install VS Build Tools, you could switch Rust to GNU toolchain:

```bash
# NOT RECOMMENDED - PyO3 works better with MSVC
rustup toolchain install stable-x86_64-pc-windows-gnu
rustup default stable-x86_64-pc-windows-gnu
```

**Issues with this approach**:
- PyO3 Python bindings may have compatibility issues
- Some Windows APIs won't work
- numpy still needs MSVC to build

---

## Summary

**What you need to do**:
1. Open Visual Studio Installer
2. Click "Modify" on Build Tools 2022
3. Check "Desktop development with C++"
4. Click Modify and wait for install
5. Open NEW terminal
6. Run `cargo build --release` in `core/ncf-rust`
7. Run `pip install -r requirements.txt` in venv

**Expected timeline**:
- VS Install: 10-15 minutes (download + install)
- Rust build: 5-10 minutes (first build is slow)
- Python deps: 5-10 minutes (numpy compilation)
- **Total**: ~30 minutes

---

## After Successful Installation

Once everything builds successfully, you can proceed to:

1. ✅ Run Rust unit tests: `cargo test` (30 tests)
2. ✅ Build Python extension: `maturin develop --release`
3. ✅ Run integration tests: `pytest tests/test_rust_integration.py`
4. ✅ Run benchmarks: `python tests/benchmark_rust_vs_python.py`
5. ✅ Verify 1.5-2x performance improvement over Python NCF v1.1

---

## Need Help?

If you encounter issues:
1. Check the error messages carefully
2. Ensure you have admin rights
3. Make sure you have ~10 GB free space
4. Restart computer if PATH issues persist

---

**Status**: Waiting for you to complete Visual Studio Build Tools installation
**Next**: Once installed, we'll build NCF v2.0 and run benchmarks!

