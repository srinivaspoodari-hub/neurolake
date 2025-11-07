"""
NeuroLake Notebook Export Utilities
Export notebooks to various formats: Jupyter, HTML, PDF
"""

import json
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path


class NotebookExporter:
    """Export NeuroLake notebooks to various formats"""

    @staticmethod
    def to_jupyter(notebook: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert NeuroLake notebook to Jupyter format (.ipynb)

        Args:
            notebook: NeuroLake notebook dictionary with cells

        Returns:
            Jupyter notebook JSON structure
        """
        jupyter_nb = {
            "cells": [],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "codemirror_mode": {"name": "ipython", "version": 3},
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.11.0"
                },
                "neurolake": {
                    "notebook_id": notebook.get('notebook_id'),
                    "name": notebook.get('name'),
                    "version": notebook.get('version'),
                    "exported_at": datetime.now().isoformat()
                }
            },
            "nbformat": 4,
            "nbformat_minor": 5
        }

        # Convert cells
        for cell in notebook.get('cells', []):
            jupyter_cell = NotebookExporter._convert_cell_to_jupyter(cell)
            jupyter_nb['cells'].append(jupyter_cell)

        return jupyter_nb

    @staticmethod
    def _convert_cell_to_jupyter(cell: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single NeuroLake cell to Jupyter cell format"""
        language = cell.get('language', 'python')
        code = cell.get('code', '')

        # Determine cell type
        if language == 'nlp':
            # NLP cells become markdown with code
            return {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    f"**NLP Query:**\n\n```\n{code}\n```\n"
                ]
            }
        else:
            # Code cell
            jupyter_cell = {
                "cell_type": "code",
                "execution_count": cell.get('execution_count', None),
                "metadata": {
                    "neurolake_language": language
                },
                "source": code.split('\n') if code else []
            }

            # Add outputs if available
            if cell.get('output'):
                jupyter_cell['outputs'] = NotebookExporter._convert_output_to_jupyter(
                    cell['output']
                )
            else:
                jupyter_cell['outputs'] = []

            return jupyter_cell

    @staticmethod
    def _convert_output_to_jupyter(output: Dict[str, Any]) -> List[Dict]:
        """Convert NeuroLake output to Jupyter output format"""
        outputs = []

        if output.get('status') == 'success':
            # Execution result
            if output.get('output'):
                outputs.append({
                    "output_type": "execute_result",
                    "execution_count": 1,
                    "data": {
                        "text/plain": [str(output['output'])]
                    },
                    "metadata": {}
                })
        else:
            # Error output
            outputs.append({
                "output_type": "error",
                "ename": "ExecutionError",
                "evalue": str(output.get('error', 'Unknown error')),
                "traceback": [str(output.get('error', 'Unknown error'))]
            })

        return outputs

    @staticmethod
    def to_html(notebook: Dict[str, Any]) -> str:
        """
        Convert NeuroLake notebook to standalone HTML

        Args:
            notebook: NeuroLake notebook dictionary

        Returns:
            HTML string
        """
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{notebook.get('name', 'Untitled Notebook')}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        body {{
            background-color: #f8f9fa;
            padding: 20px;
        }}
        .notebook-container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .notebook-header {{
            border-bottom: 2px solid #667eea;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .cell {{
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            overflow: hidden;
        }}
        .cell-header {{
            background: #f8f9fa;
            padding: 10px 15px;
            border-bottom: 1px solid #dee2e6;
            font-weight: 600;
        }}
        .cell-content {{
            padding: 15px;
        }}
        .cell-output {{
            background: #f8f9fa;
            padding: 15px;
            border-top: 1px solid #dee2e6;
        }}
        pre {{
            background: #282c34;
            padding: 15px;
            border-radius: 5px;
            margin: 0;
        }}
        .language-badge {{
            background: #667eea;
            color: white;
            padding: 3px 10px;
            border-radius: 10px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="notebook-container">
        <div class="notebook-header">
            <h1>{notebook.get('name', 'Untitled Notebook')}</h1>
            <p class="text-muted mb-0">
                Exported from NeuroLake • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>

        <div class="cells">
"""

        # Add cells
        for i, cell in enumerate(notebook.get('cells', [])):
            language = cell.get('language', 'python')
            code = cell.get('code', '')

            html += f"""
        <div class="cell">
            <div class="cell-header">
                <span class="language-badge">{language.upper()}</span>
                Cell {i + 1}
            </div>
            <div class="cell-content">
                <pre><code class="language-{language}">{code}</code></pre>
            </div>
"""

            # Add output if available
            if cell.get('output'):
                output = cell['output']
                status_class = 'success' if output.get('status') == 'success' else 'danger'

                html += f"""
            <div class="cell-output">
                <div class="alert alert-{status_class} mb-0">
                    <strong>Output:</strong><br>
                    <pre class="mb-0">{json.dumps(output.get('output'), indent=2)}</pre>
                </div>
            </div>
"""

            html += "        </div>\n"

        html += """
        </div>
    </div>

    <script>
        hljs.highlightAll();
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
        return html

    @staticmethod
    def save_jupyter(notebook: Dict[str, Any], output_path: str) -> str:
        """
        Save notebook as Jupyter .ipynb file

        Args:
            notebook: NeuroLake notebook dictionary
            output_path: Path to save the file

        Returns:
            Path to saved file
        """
        jupyter_nb = NotebookExporter.to_jupyter(notebook)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(jupyter_nb, f, indent=2)

        return str(output_file)

    @staticmethod
    def save_html(notebook: Dict[str, Any], output_path: str) -> str:
        """
        Save notebook as HTML file

        Args:
            notebook: NeuroLake notebook dictionary
            output_path: Path to save the file

        Returns:
            Path to saved file
        """
        html_content = NotebookExporter.to_html(notebook)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(output_file)


# Example usage
if __name__ == "__main__":
    # Sample notebook
    sample_notebook = {
        "notebook_id": "test-123",
        "name": "Sample Analysis",
        "version": "1.0",
        "cells": [
            {
                "language": "python",
                "code": "import pandas as pd\ndf = pd.DataFrame({'a': [1, 2, 3]})",
                "execution_count": 1,
                "output": {
                    "status": "success",
                    "output": "DataFrame created"
                }
            },
            {
                "language": "sql",
                "code": "SELECT * FROM customers LIMIT 10",
                "execution_count": 2,
                "output": {
                    "status": "success",
                    "output": [{"id": 1, "name": "Alice"}]
                }
            }
        ]
    }

    # Export to Jupyter
    exporter = NotebookExporter()
    jupyter_path = exporter.save_jupyter(sample_notebook, "C:/NeuroLake/exports/sample.ipynb")
    print(f"Exported to Jupyter: {jupyter_path}")

    # Export to HTML
    html_path = exporter.save_html(sample_notebook, "C:/NeuroLake/exports/sample.html")
    print(f"Exported to HTML: {html_path}")
