/**
 * NeuroLake Unified Dashboard - Frontend JavaScript
 * ================================================
 *
 * Integrates all NeuroLake features into a single interface:
 * - SQL Query Editor with Monaco
 * - Real-time monitoring via WebSocket
 * - Interactive data visualization
 * - NCF format management
 * - AI-powered insights
 */

let editor;
let queryChart, storageChart, cpuChart, memoryChart, ncfChart;
let ws;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeEditor();
    initializeCharts();
    loadSystemStatus();
    connectWebSocket();
    loadQueryHistory();

    // Auto-refresh every 30 seconds
    setInterval(loadSystemStatus, 30000);
});

// ==================== Monaco Editor ====================

function initializeEditor() {
    require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.44.0/min/vs' } });

    require(['vs/editor/editor.main'], function() {
        editor = monaco.editor.create(document.getElementById('query-editor'), {
            value: '-- Welcome to NeuroLake SQL Editor\n-- Press Ctrl+Enter to execute\n\nSELECT * FROM users LIMIT 10;',
            language: 'sql',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: true },
            fontSize: 14,
            lineNumbers: 'on',
            roundedSelection: false,
            scrollBeyondLastLine: false,
            readOnly: false,
        });

        // Add keyboard shortcut for execution
        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, executeQuery);

        // SQL language features
        monaco.languages.registerCompletionItemProvider('sql', {
            provideCompletionItems: (model, position) => {
                const suggestions = [
                    { label: 'SELECT', kind: monaco.languages.CompletionItemKind.Keyword, insertText: 'SELECT ' },
                    { label: 'FROM', kind: monaco.languages.CompletionItemKind.Keyword, insertText: 'FROM ' },
                    { label: 'WHERE', kind: monaco.languages.CompletionItemKind.Keyword, insertText: 'WHERE ' },
                    { label: 'GROUP BY', kind: monaco.languages.CompletionItemKind.Keyword, insertText: 'GROUP BY ' },
                    { label: 'ORDER BY', kind: monaco.languages.CompletionItemKind.Keyword, insertText: 'ORDER BY ' },
                    { label: 'LIMIT', kind: monaco.languages.CompletionItemKind.Keyword, insertText: 'LIMIT ' },
                ];
                return { suggestions: suggestions };
            }
        });
    });
}

// ==================== Query Execution ====================

async function executeQuery() {
    const sql = editor.getValue();
    const database = document.getElementById('database-select').value;

    showQueryStatus('info', 'Executing query...');

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sql, database })
        });

        const result = await response.json();

        if (result.success) {
            displayQueryResults(result);
            showQueryStatus('success', `Query executed successfully in ${result.execution_time_ms.toFixed(2)}ms. Rows: ${result.row_count}`);
        } else {
            showQueryStatus('danger', `Error: ${result.error}`);
        }
    } catch (error) {
        showQueryStatus('danger', `Request failed: ${error.message}`);
    }
}

function displayQueryResults(result) {
    const table = document.getElementById('results-table');
    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');

    // Clear previous results
    thead.innerHTML = '';
    tbody.innerHTML = '';

    if (!result.data || result.data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="100" class="text-center text-muted">No results</td></tr>';
        return;
    }

    // Create header
    const headerRow = document.createElement('tr');
    result.columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);

    // Create rows
    result.data.forEach(row => {
        const tr = document.createElement('tr');
        result.columns.forEach(col => {
            const td = document.createElement('td');
            td.textContent = row[col] !== null ? row[col] : 'NULL';
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    // Update metrics tab
    document.getElementById('query-metrics').innerHTML = `
        <div class="row">
            <div class="col-md-4">
                <h6>Execution Time</h6>
                <p class="h4">${result.execution_time_ms.toFixed(2)} ms</p>
            </div>
            <div class="col-md-4">
                <h6>Rows Returned</h6>
                <p class="h4">${result.row_count}</p>
            </div>
            <div class="col-md-4">
                <h6>Query ID</h6>
                <p class="text-muted">${result.query_id || 'N/A'}</p>
            </div>
        </div>
    `;
}

function showQueryStatus(type, message) {
    const statusDiv = document.getElementById('query-status');
    statusDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    setTimeout(() => statusDiv.innerHTML = '', 5000);
}

// ==================== Format & Optimize ====================

function formatQuery() {
    const sql = editor.getValue();
    // Simple SQL formatting
    const formatted = sql
        .replace(/SELECT/gi, '\nSELECT')
        .replace(/FROM/gi, '\nFROM')
        .replace(/WHERE/gi, '\nWHERE')
        .replace(/GROUP BY/gi, '\nGROUP BY')
        .replace(/ORDER BY/gi, '\nORDER BY')
        .replace(/LIMIT/gi, '\nLIMIT');
    editor.setValue(formatted.trim());
}

async function explainQuery() {
    const sql = editor.getValue();

    try {
        const response = await fetch('/api/query/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sql })
        });

        const result = await response.json();
        document.getElementById('explain-plan').textContent = JSON.stringify(result, null, 2);
    } catch (error) {
        document.getElementById('explain-plan').textContent = `Error: ${error.message}`;
    }
}

async function optimizeQuery() {
    const sql = editor.getValue();

    showQueryStatus('info', 'AI is analyzing your query...');

    try {
        const response = await fetch('/api/query/optimize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sql })
        });

        const result = await response.json();

        if (result.optimized_sql) {
            if (confirm('Replace query with optimized version?')) {
                editor.setValue(result.optimized_sql);
            }
            showQueryStatus('success', `Optimization complete! Expected speedup: ${result.speedup}x`);
        }
    } catch (error) {
        showQueryStatus('danger', `Optimization failed: ${error.message}`);
    }
}

// ==================== System Status ====================

async function loadSystemStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();

        // Update metric cards
        document.getElementById('total-tables').textContent = status.total_tables;
        document.getElementById('queries-today').textContent = status.total_queries;
        document.getElementById('storage-used').textContent = `${status.storage_used_gb.toFixed(1)} GB`;

        // Update charts if needed
        if (queryChart) {
            updateQueryChart(status);
        }
    } catch (error) {
        console.error('Failed to load system status:', error);
    }
}

// ==================== Charts ====================

function initializeCharts() {
    // Query Performance Chart
    const queryCtx = document.getElementById('queryChart');
    if (queryCtx) {
        queryChart = new Chart(queryCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Queries/min',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }

    // Storage Chart
    const storageCtx = document.getElementById('storageChart');
    if (storageCtx) {
        storageChart = new Chart(storageCtx, {
            type: 'doughnut',
            data: {
                labels: ['NCF', 'Parquet', 'Delta', 'Other'],
                datasets: [{
                    data: [45, 30, 15, 10],
                    backgroundColor: [
                        'rgb(54, 162, 235)',
                        'rgb(255, 99, 132)',
                        'rgb(255, 205, 86)',
                        'rgb(201, 203, 207)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    // CPU Chart
    const cpuCtx = document.getElementById('cpuChart');
    if (cpuCtx) {
        cpuChart = new Chart(cpuCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU %',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    fill: true,
                    backgroundColor: 'rgba(255, 99, 132, 0.2)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, max: 100 }
                }
            }
        });
    }

    // Memory Chart
    const memoryCtx = document.getElementById('memoryChart');
    if (memoryCtx) {
        memoryChart = new Chart(memoryCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Memory %',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    fill: true,
                    backgroundColor: 'rgba(54, 162, 235, 0.2)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, max: 100 }
                }
            }
        });
    }

    // NCF Chart
    const ncfCtx = document.getElementById('ncfChart');
    if (ncfCtx) {
        ncfChart = new Chart(ncfCtx, {
            type: 'bar',
            data: {
                labels: ['Original', 'NCF Compressed', 'Savings'],
                datasets: [{
                    label: 'Size (GB)',
                    data: [100, 35, 65],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(54, 162, 235, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
}

function updateQueryChart(status) {
    const now = new Date().toLocaleTimeString();

    if (queryChart.data.labels.length > 20) {
        queryChart.data.labels.shift();
        queryChart.data.datasets[0].data.shift();
    }

    queryChart.data.labels.push(now);
    queryChart.data.datasets[0].data.push(Math.random() * 100);
    queryChart.update();
}

// ==================== WebSocket for Real-time Updates ====================

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/monitoring`);

    ws.onmessage = (event) => {
        const metrics = JSON.parse(event.data);
        updateRealTimeMetrics(metrics);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket closed. Reconnecting...');
        setTimeout(connectWebSocket, 5000);
    };
}

function updateRealTimeMetrics(metrics) {
    // Update CPU chart
    if (cpuChart && metrics.cpu_percent !== undefined) {
        const now = new Date().toLocaleTimeString();

        if (cpuChart.data.labels.length > 30) {
            cpuChart.data.labels.shift();
            cpuChart.data.datasets[0].data.shift();
        }

        cpuChart.data.labels.push(now);
        cpuChart.data.datasets[0].data.push(metrics.cpu_percent);
        cpuChart.update('none');
    }

    // Update memory chart
    if (memoryChart && metrics.memory_percent !== undefined) {
        const now = new Date().toLocaleTimeString();

        if (memoryChart.data.labels.length > 30) {
            memoryChart.data.labels.shift();
            memoryChart.data.datasets[0].data.shift();
        }

        memoryChart.data.labels.push(now);
        memoryChart.data.datasets[0].data.push(metrics.memory_percent);
        memoryChart.update('none');
    }
}

// ==================== Tab Navigation ====================

function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-pane').forEach(tab => {
        tab.style.display = 'none';
    });

    // Show selected tab
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.style.display = 'block';
    }

    // Update sidebar active state
    document.querySelectorAll('.sidebar a').forEach(link => {
        link.classList.remove('active');
    });
    event.target.classList.add('active');
}

// ==================== Query History ====================

async function loadQueryHistory() {
    try {
        const response = await fetch('/api/query-history?limit=10');
        const data = await response.json();

        const tbody = document.getElementById('activity-table');
        tbody.innerHTML = '';

        data.queries.forEach(query => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${new Date(query.timestamp).toLocaleTimeString()}</td>
                <td>${query.user || 'admin'}</td>
                <td><code>${query.sql.substring(0, 50)}...</code></td>
                <td><span class="badge bg-success">Success</span></td>
                <td>${query.execution_time_ms.toFixed(2)}ms</td>
            `;
        });
    } catch (error) {
        console.error('Failed to load query history:', error);
    }
}

// ==================== NCF Management ====================

async function convertToNCF(event) {
    event.preventDefault();

    const sourceTable = document.getElementById('ncf-source-table').value;
    const compression = document.getElementById('ncf-compression').value;

    try {
        const response = await fetch('/api/ncf/convert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source_table: sourceTable, compression })
        });

        const result = await response.json();

        if (result.success) {
            alert(`Successfully converted to NCF!\nOriginal: ${result.original_size_mb}MB\nCompressed: ${result.compressed_size_mb}MB\nSavings: ${result.compression_ratio}x`);

            // Update NCF chart
            if (ncfChart) {
                ncfChart.data.datasets[0].data = [
                    result.original_size_mb,
                    result.compressed_size_mb,
                    result.original_size_mb - result.compressed_size_mb
                ];
                ncfChart.update();
            }
        }
    } catch (error) {
        alert(`Conversion failed: ${error.message}`);
    }
}

// ==================== Data Explorer ====================

async function loadTableTree() {
    try {
        const response = await fetch('/api/tables');
        const data = await response.json();

        const tree = document.getElementById('table-tree');
        tree.innerHTML = '';

        const databases = {};
        data.tables.forEach(table => {
            if (!databases[table.database]) {
                databases[table.database] = [];
            }
            databases[table.database].push(table.name);
        });

        for (const [db, tables] of Object.entries(databases)) {
            const dbNode = document.createElement('div');
            dbNode.innerHTML = `
                <div class="fw-bold mt-2">
                    <i class="fas fa-database"></i> ${db}
                </div>
            `;

            tables.forEach(table => {
                const tableNode = document.createElement('div');
                tableNode.className = 'ms-3 mt-1';
                tableNode.innerHTML = `
                    <a href="#" onclick="previewTable('${db}', '${table}'); return false;">
                        <i class="fas fa-table"></i> ${table}
                    </a>
                `;
                dbNode.appendChild(tableNode);
            });

            tree.appendChild(dbNode);
        }
    } catch (error) {
        console.error('Failed to load table tree:', error);
    }
}

async function previewTable(database, table) {
    try {
        const response = await fetch(`/api/tables/${database}/${table}`);
        const info = await response.json();

        const preview = document.getElementById('table-preview');
        preview.innerHTML = `
            <h5>${database}.${table}</h5>
            <div class="row mt-3">
                <div class="col-md-6">
                    <p><strong>Format:</strong> ${info.format}</p>
                    <p><strong>Rows:</strong> ${info.row_count.toLocaleString()}</p>
                    <p><strong>Size:</strong> ${(info.size_bytes / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Created:</strong> ${new Date(info.created_at).toLocaleString()}</p>
                    <p><strong>Updated:</strong> ${new Date(info.updated_at).toLocaleString()}</p>
                </div>
            </div>
            <h6 class="mt-3">Schema</h6>
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Column</th>
                        <th>Type</th>
                        <th>Nullable</th>
                    </tr>
                </thead>
                <tbody>
                    ${Object.entries(info.schema).map(([col, type]) => `
                        <tr>
                            <td><code>${col}</code></td>
                            <td>${type}</td>
                            <td>Yes</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            <button class="btn btn-primary btn-sm mt-3" onclick="queryTable('${database}', '${table}')">
                Query Table
            </button>
            <button class="btn btn-secondary btn-sm mt-3" onclick="convertTableToNCF('${database}', '${table}')">
                Convert to NCF
            </button>
        `;
    } catch (error) {
        console.error('Failed to preview table:', error);
    }
}

function queryTable(database, table) {
    editor.setValue(`SELECT * FROM ${database}.${table} LIMIT 100;`);
    showTab('query');
}

function convertTableToNCF(database, table) {
    document.getElementById('ncf-source-table').value = `${database}.${table}`;
    showTab('ncf');
}

// Initialize data explorer when tab is shown
document.addEventListener('DOMContentLoaded', () => {
    const dataTab = document.querySelector('a[href="#data"]');
    if (dataTab) {
        dataTab.addEventListener('click', loadTableTree);
    }
});
