# 🗂️ S3-Like File Browser Enhancement Plan

**Date:** November 3, 2025
**Status:** 📋 PLANNING
**Requested By:** User - "unable to navigate Storage & NCF Files from UI and it's folder structure, it should function that all S3 does all operations it should support"

---

## 🎯 Goal

Transform the current **Storage & NCF Files** tab into a full-featured S3-compatible file browser with:
- Folder tree navigation (like AWS S3 Console)
- All file operations (upload, download, delete, rename, copy, move)
- All folder operations (create, delete, navigate)
- Breadcrumb navigation
- File preview capabilities
- Drag-and-drop upload
- Multi-select operations

---

## 📊 Current State

### What We Have Now
- ✅ List buckets
- ✅ List NCF files (flat list, no folders)
- ✅ Show file sizes and metadata
- ❌ No folder navigation
- ❌ No file operations
- ❌ No upload/download
- ❌ No folder structure visualization

### What's Missing
- ❌ Folder tree/hierarchy navigation
- ❌ Breadcrumb path display
- ❌ File upload functionality
- ❌ File download functionality
- ❌ File delete functionality
- ❌ File rename/move/copy operations
- ❌ Folder create/delete operations
- ❌ File preview (images, text files)
- ❌ Multi-select operations
- ❌ Search within bucket/folder
- ❌ Sorting by name/size/date

---

## 🏗️ Architecture Design

### Backend API Endpoints to Add

#### 1. **Browse Folder/Bucket**
```python
@app.get("/api/storage/browse")
async def browse_storage(bucket: str, prefix: str = ""):
    """
    Browse files and folders in a bucket with prefix
    Returns: {
        "folders": [...],  # Virtual folders (prefixes)
        "files": [...],    # Actual files
        "current_path": "bucket/path/to/folder",
        "breadcrumbs": [...]
    }
    """
```

#### 2. **Upload File**
```python
@app.post("/api/storage/upload")
async def upload_file(bucket: str, path: str, file: UploadFile):
    """Upload file to MinIO bucket"""
```

#### 3. **Download File**
```python
@app.get("/api/storage/download")
async def download_file(bucket: str, path: str):
    """Download file from MinIO bucket"""
```

#### 4. **Delete File**
```python
@app.delete("/api/storage/file")
async def delete_file(bucket: str, path: str):
    """Delete file from MinIO bucket"""
```

#### 5. **Delete Folder**
```python
@app.delete("/api/storage/folder")
async def delete_folder(bucket: str, prefix: str):
    """Delete all files with prefix (folder)"""
```

#### 6. **Rename/Move File**
```python
@app.put("/api/storage/move")
async def move_file(bucket: str, source: str, destination: str):
    """Move/rename file in MinIO"""
```

#### 7. **Copy File**
```python
@app.post("/api/storage/copy")
async def copy_file(source_bucket: str, source_path: str,
                   dest_bucket: str, dest_path: str):
    """Copy file within or across buckets"""
```

#### 8. **Create Folder**
```python
@app.post("/api/storage/folder")
async def create_folder(bucket: str, path: str):
    """Create virtual folder (by creating .keep file)"""
```

#### 9. **Get File Metadata**
```python
@app.get("/api/storage/file/metadata")
async def get_file_metadata(bucket: str, path: str):
    """Get detailed file metadata"""
```

#### 10. **Search Files**
```python
@app.get("/api/storage/search")
async def search_files(bucket: str, query: str, prefix: str = ""):
    """Search files in bucket"""
```

---

## 🎨 Frontend UI Design

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Storage & NCF Files                                         │
├─────────────────────────────────────────────────────────────┤
│  📊 Metrics: Total: 1.5GB | Buckets: 2 | Files: 54          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌───────────────────────────────────┐   │
│  │ Buckets      │  │ File Browser                       │   │
│  │              │  │                                     │   │
│  │ 📁 neurolake │  │ 🏠 > neurolake-data > sales > 2025│   │
│  │    -data ✓   │  │ ─────────────────────────────────  │   │
│  │              │  │ [🔍 Search] [⬆️ Upload] [➕ Folder]│   │
│  │ 📁 neurolake │  │                                     │   │
│  │    -backups  │  │ ┌─┬─────────┬──────┬──────┬─────┐ │   │
│  │              │  │ │☑│ Name    │ Size │ Date │ ... │ │   │
│  │              │  │ ├─┼─────────┼──────┼──────┼─────┤ │   │
│  │              │  │ │ │📁 data  │  --  │      │  ⋮  │ │   │
│  │              │  │ │ │📁 logs  │  --  │      │  ⋮  │ │   │
│  │              │  │ │ │📄 q1.ncf│ 50MB │ ...  │  ⋮  │ │   │
│  │              │  │ │ │📄 q2.ncf│ 45MB │ ...  │  ⋮  │ │   │
│  │              │  │ └─┴─────────┴──────┴──────┴─────┘ │   │
│  └──────────────┘  └───────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### UI Components

#### 1. **Bucket List (Left Sidebar)**
- List all buckets
- Click to select/browse
- Show bucket stats

#### 2. **Breadcrumb Navigation**
- Show current path: `Home > bucket > folder1 > folder2`
- Click any breadcrumb to navigate up
- Copy path button

#### 3. **Action Toolbar**
- **Search Bar:** Filter files/folders
- **Upload Button:** Upload files (with drag-drop)
- **New Folder Button:** Create new folder
- **Refresh Button:** Reload current view
- **View Toggle:** Grid view / List view

#### 4. **File/Folder Table**
- **Columns:**
  - Checkbox (for multi-select)
  - Icon (folder/file type)
  - Name (clickable)
  - Size
  - Last Modified
  - Actions (⋮ menu)

- **Row Actions (⋮ menu):**
  - Download
  - Rename
  - Move
  - Copy
  - Delete
  - Properties

#### 5. **Context Menu (Right-Click)**
- Upload Here
- New Folder
- Paste
- Refresh
- (On file/folder):
  - Open
  - Download
  - Rename
  - Move To...
  - Copy
  - Delete

#### 6. **Multi-Select Actions Bar**
When files are selected:
```
[✓ 3 items selected] Download | Delete | Move | Copy [✕ Clear]
```

#### 7. **File Preview Modal**
For supported file types:
- Images: Show thumbnail
- Text files: Show content
- NCF files: Show schema/metadata
- JSON/CSV: Formatted view

---

## 🔧 Implementation Steps

### Phase 1: Backend API (Priority 1)
1. ✅ Add file upload endpoint
2. ✅ Add file download endpoint
3. ✅ Add browse with prefix endpoint
4. ✅ Add delete file endpoint
5. ✅ Add rename/move endpoint
6. ✅ Add copy endpoint
7. ✅ Add folder create/delete endpoints

### Phase 2: Frontend Basic Navigation (Priority 1)
1. ✅ Add bucket selector
2. ✅ Add breadcrumb navigation
3. ✅ Add folder/file table with hierarchy
4. ✅ Make folders clickable to navigate

### Phase 3: File Operations UI (Priority 2)
1. ✅ Add upload button with file picker
2. ✅ Add download functionality
3. ✅ Add delete confirmation dialog
4. ✅ Add action menu (⋮) for each row

### Phase 4: Advanced Features (Priority 3)
1. ⏳ Drag-and-drop upload
2. ⏳ Multi-select with checkboxes
3. ⏳ Context menu (right-click)
4. ⏳ File preview modal
5. ⏳ Search functionality
6. ⏳ Sorting by columns

---

## 📝 Detailed Implementation

### Backend: Browse Endpoint

```python
@app.get("/api/storage/browse")
async def browse_storage(bucket: str, prefix: str = ""):
    """
    Browse files and folders in MinIO bucket

    Args:
        bucket: Bucket name
        prefix: Current folder path (e.g., "sales/2025/")

    Returns:
        {
            "status": "success",
            "bucket": "neurolake-data",
            "prefix": "sales/2025/",
            "folders": [
                {"name": "q1", "full_path": "sales/2025/q1/"},
                {"name": "q2", "full_path": "sales/2025/q2/"}
            ],
            "files": [
                {
                    "name": "summary.ncf",
                    "full_path": "sales/2025/summary.ncf",
                    "size": 52428800,
                    "size_formatted": "50.00 MB",
                    "modified": "2025-11-01T12:00:00",
                    "etag": "abc123"
                }
            ],
            "breadcrumbs": [
                {"name": "Home", "path": ""},
                {"name": "sales", "path": "sales/"},
                {"name": "2025", "path": "sales/2025/"}
            ]
        }
    """
    global minio_client
    try:
        if not minio_client:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "message": "MinIO not connected"}
            )

        # Normalize prefix
        if prefix and not prefix.endswith('/'):
            prefix += '/'

        # List objects with prefix
        objects = minio_client.list_objects(bucket, prefix=prefix, recursive=False)

        folders = []
        files = []
        seen_folders = set()

        for obj in objects:
            # Remove prefix to get relative path
            relative_path = obj.object_name[len(prefix):]

            if obj.is_dir or relative_path.endswith('/'):
                # It's a folder
                folder_name = relative_path.rstrip('/')
                if folder_name and folder_name not in seen_folders:
                    folders.append({
                        "name": folder_name,
                        "full_path": obj.object_name
                    })
                    seen_folders.add(folder_name)
            else:
                # It's a file
                files.append({
                    "name": relative_path,
                    "full_path": obj.object_name,
                    "size": obj.size,
                    "size_formatted": format_bytes(obj.size),
                    "modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag
                })

        # Build breadcrumbs
        breadcrumbs = [{"name": "Home", "path": ""}]
        if prefix:
            parts = prefix.rstrip('/').split('/')
            current_path = ""
            for part in parts:
                current_path += part + '/'
                breadcrumbs.append({"name": part, "path": current_path})

        return {
            "status": "success",
            "bucket": bucket,
            "prefix": prefix,
            "folders": sorted(folders, key=lambda x: x['name']),
            "files": sorted(files, key=lambda x: x['name']),
            "breadcrumbs": breadcrumbs
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )
```

### Backend: Upload Endpoint

```python
@app.post("/api/storage/upload")
async def upload_file(bucket: str = Form(...),
                     path: str = Form(...),
                     file: UploadFile = File(...)):
    """
    Upload file to MinIO

    Args:
        bucket: Target bucket name
        path: Target path (prefix) in bucket
        file: File to upload

    Returns:
        {
            "status": "success",
            "message": "File uploaded successfully",
            "file_path": "sales/2025/data.ncf"
        }
    """
    global minio_client
    try:
        if not minio_client:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "message": "MinIO not connected"}
            )

        # Build full object name
        object_name = path.rstrip('/') + '/' + file.filename if path else file.filename

        # Upload file
        content = await file.read()
        minio_client.put_object(
            bucket,
            object_name,
            io.BytesIO(content),
            length=len(content),
            content_type=file.content_type or 'application/octet-stream'
        )

        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded successfully",
            "file_path": object_name
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )
```

### Frontend: File Browser Component

```javascript
// Storage browser state
let currentBucket = null;
let currentPrefix = "";
let selectedFiles = [];

// Load bucket contents
async function browseBucket(bucket, prefix = "") {
    currentBucket = bucket;
    currentPrefix = prefix;

    try {
        const response = await fetch(`/api/storage/browse?bucket=${bucket}&prefix=${encodeURIComponent(prefix)}`);
        const data = await response.json();

        if (data.status === 'success') {
            renderBreadcrumbs(data.breadcrumbs);
            renderFileList(data.folders, data.files);
        }
    } catch (error) {
        console.error('Error browsing bucket:', error);
    }
}

// Render breadcrumbs
function renderBreadcrumbs(breadcrumbs) {
    const html = breadcrumbs.map(crumb => `
        <a href="#" onclick="browseBucket('${currentBucket}', '${crumb.path}'); return false;">
            ${crumb.name}
        </a>
    `).join(' <i class="bi bi-chevron-right"></i> ');

    document.getElementById('breadcrumbs').innerHTML = html;
}

// Render file/folder list
function renderFileList(folders, files) {
    let html = '<table class="table table-hover">';
    html += '<thead><tr><th><input type="checkbox" id="select-all"></th>';
    html += '<th>Name</th><th>Size</th><th>Modified</th><th>Actions</th></tr></thead><tbody>';

    // Folders first
    folders.forEach(folder => {
        html += `
            <tr onclick="browseBucket('${currentBucket}', '${folder.full_path}')">
                <td><input type="checkbox" class="file-checkbox"></td>
                <td><i class="bi bi-folder-fill"></i> ${folder.name}</td>
                <td>--</td>
                <td>--</td>
                <td>
                    <div class="dropdown">
                        <button class="btn btn-sm" data-bs-toggle="dropdown">⋮</button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#">Delete Folder</a></li>
                        </ul>
                    </div>
                </td>
            </tr>
        `;
    });

    // Then files
    files.forEach(file => {
        html += `
            <tr>
                <td><input type="checkbox" class="file-checkbox" data-path="${file.full_path}"></td>
                <td><i class="bi bi-file-earmark"></i> ${file.name}</td>
                <td>${file.size_formatted}</td>
                <td>${new Date(file.modified).toLocaleString()}</td>
                <td>
                    <div class="dropdown">
                        <button class="btn btn-sm" data-bs-toggle="dropdown">⋮</button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" onclick="downloadFile('${file.full_path}')">Download</a></li>
                            <li><a class="dropdown-item" onclick="renameFile('${file.full_path}')">Rename</a></li>
                            <li><a class="dropdown-item" onclick="deleteFile('${file.full_path}')">Delete</a></li>
                        </ul>
                    </div>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    document.getElementById('file-list').innerHTML = html;
}

// Upload file
async function uploadFile() {
    const fileInput = document.getElementById('file-upload-input');
    const file = fileInput.files[0];

    if (!file) {
        alert('Please select a file');
        return;
    }

    const formData = new FormData();
    formData.append('bucket', currentBucket);
    formData.append('path', currentPrefix);
    formData.append('file', file);

    try {
        const response = await fetch('/api/storage/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.status === 'success') {
            alert(data.message);
            browseBucket(currentBucket, currentPrefix); // Refresh
        } else {
            alert('Upload failed: ' + data.message);
        }
    } catch (error) {
        alert('Upload error: ' + error);
    }
}

// Download file
async function downloadFile(path) {
    window.open(`/api/storage/download?bucket=${currentBucket}&path=${encodeURIComponent(path)}`);
}

// Delete file
async function deleteFile(path) {
    if (!confirm(`Delete file "${path}"?`)) return;

    try {
        const response = await fetch(`/api/storage/file?bucket=${currentBucket}&path=${encodeURIComponent(path)}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.status === 'success') {
            alert('File deleted');
            browseBucket(currentBucket, currentPrefix); // Refresh
        }
    } catch (error) {
        alert('Delete error: ' + error);
    }
}
```

---

## 🎯 Success Criteria

When complete, users should be able to:

✅ **Navigate:**
- Click through folder hierarchy
- Use breadcrumbs to go back
- Switch between buckets

✅ **Upload:**
- Click upload button to select files
- Drag and drop files
- See upload progress

✅ **Download:**
- Download individual files
- Download multiple files (as zip)

✅ **Delete:**
- Delete files with confirmation
- Delete folders with all contents
- Delete multiple selected items

✅ **Organize:**
- Create new folders
- Rename files/folders
- Move files between folders
- Copy files

✅ **Search:**
- Search files by name
- Filter by file type
- Sort by name/size/date

---

## ⏱️ Estimated Implementation Time

- **Phase 1 (Backend API):** 2-3 hours
- **Phase 2 (Basic Navigation):** 2-3 hours
- **Phase 3 (File Operations):** 2-3 hours
- **Phase 4 (Advanced Features):** 3-4 hours

**Total:** 9-13 hours of development

---

## 📋 Next Steps

1. Review and approve this plan
2. Implement Phase 1 (Backend API endpoints)
3. Implement Phase 2 (Basic navigation UI)
4. Implement Phase 3 (File operations)
5. Implement Phase 4 (Advanced features)
6. Test all functionality
7. Document usage

---

**Status:** 📋 PLAN READY FOR REVIEW
**Date:** November 3, 2025
