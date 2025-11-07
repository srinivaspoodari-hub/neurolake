"""
NeuroLake Visual Sync Layer
Bi-directional synchronization between visual pipeline JSON and code (Python/PySpark)
"""

import ast
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re


class NodeType(Enum):
    """Pipeline node types"""
    READ = "read"
    WRITE = "write"
    FILTER = "filter"
    SELECT = "select"
    JOIN = "join"
    AGGREGATE = "aggregate"
    SORT = "sort"
    UNION = "union"
    TRANSFORM = "transform"
    CUSTOM = "custom"


class Language(Enum):
    """Supported code languages"""
    PYTHON = "python"
    PYSPARK = "pyspark"
    SQL = "sql"
    SCALA = "scala"


@dataclass
class PipelineNode:
    """Represents a single node in the visual pipeline"""
    id: str
    type: NodeType
    config: Dict[str, Any]
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineEdge:
    """Represents a connection between nodes"""
    id: str
    source: str  # source node id
    target: str  # target node id
    source_port: Optional[str] = None
    target_port: Optional[str] = None


@dataclass
class PipelineDefinition:
    """Complete pipeline definition"""
    id: str
    name: str
    nodes: List[PipelineNode]
    edges: List[PipelineEdge]
    metadata: Dict[str, Any] = field(default_factory=dict)


class CodeParser:
    """Parse code (Python/PySpark) to extract pipeline structure"""

    def parse_pyspark_code(self, code: str) -> PipelineDefinition:
        """Parse PySpark code into pipeline definition"""
        try:
            tree = ast.parse(code)
            nodes = []
            edges = []
            node_counter = 0

            # Track variable assignments to build data flow
            var_to_node = {}

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    # Extract assignment: df = spark.read.table('customers')
                    target_var = self._get_assignment_target(node)
                    operation, config = self._extract_operation(node.value)

                    if operation:
                        node_id = f"node_{node_counter}"
                        node_counter += 1

                        pipeline_node = PipelineNode(
                            id=node_id,
                            type=operation,
                            config=config,
                            position={"x": 100 + (node_counter * 200), "y": 100}
                        )
                        nodes.append(pipeline_node)
                        var_to_node[target_var] = node_id

                        # Detect edges from dependencies
                        dependencies = self._extract_dependencies(node.value)
                        for dep_var in dependencies:
                            if dep_var in var_to_node:
                                edge_id = f"edge_{len(edges)}"
                                edges.append(PipelineEdge(
                                    id=edge_id,
                                    source=var_to_node[dep_var],
                                    target=node_id
                                ))

            return PipelineDefinition(
                id="pipeline_1",
                name="Parsed Pipeline",
                nodes=nodes,
                edges=edges,
                metadata={"language": "pyspark", "source": "code_parser"}
            )
        except Exception as e:
            raise ValueError(f"Failed to parse PySpark code: {e}")

    def _get_assignment_target(self, node: ast.Assign) -> str:
        """Extract variable name from assignment"""
        if node.targets and isinstance(node.targets[0], ast.Name):
            return node.targets[0].id
        return "unknown"

    def _extract_operation(self, node: ast.AST) -> Tuple[Optional[NodeType], Dict]:
        """Extract operation type and configuration from AST node"""
        config = {}

        if isinstance(node, ast.Call):
            func_name = self._get_function_name(node.func)

            # spark.read.table() or spark.read.parquet()
            if 'read' in func_name:
                if 'table' in func_name:
                    config['source'] = self._extract_string_arg(node, 0)
                    config['source_type'] = 'table'
                elif 'parquet' in func_name:
                    config['source'] = self._extract_string_arg(node, 0)
                    config['source_type'] = 'parquet'
                elif 'csv' in func_name:
                    config['source'] = self._extract_string_arg(node, 0)
                    config['source_type'] = 'csv'
                return NodeType.READ, config

            # df.write.table() or df.write.saveAsTable()
            elif 'write' in func_name or 'saveAsTable' in func_name:
                config['target'] = self._extract_string_arg(node, 0)
                config['target_type'] = 'table'
                return NodeType.WRITE, config

            # df.filter()
            elif 'filter' in func_name:
                config['condition'] = self._extract_filter_condition(node)
                return NodeType.FILTER, config

            # df.select()
            elif 'select' in func_name:
                config['columns'] = self._extract_columns(node)
                return NodeType.SELECT, config

            # df.join()
            elif 'join' in func_name:
                config['join_type'] = self._extract_join_type(node)
                config['condition'] = self._extract_join_condition(node)
                return NodeType.JOIN, config

            # df.groupBy() or df.agg()
            elif 'groupBy' in func_name or 'agg' in func_name:
                config['group_by'] = self._extract_columns(node)
                return NodeType.AGGREGATE, config

            # df.orderBy() or df.sort()
            elif 'orderBy' in func_name or 'sort' in func_name:
                config['columns'] = self._extract_columns(node)
                return NodeType.SORT, config

            # df.union()
            elif 'union' in func_name:
                return NodeType.UNION, config

        return None, config

    def _get_function_name(self, node: ast.AST) -> str:
        """Get full function name including attributes"""
        if isinstance(node, ast.Attribute):
            base = self._get_function_name(node.value)
            return f"{base}.{node.attr}"
        elif isinstance(node, ast.Name):
            return node.id
        return ""

    def _extract_string_arg(self, node: ast.Call, index: int) -> str:
        """Extract string argument at given index"""
        if len(node.args) > index and isinstance(node.args[index], ast.Constant):
            return str(node.args[index].value)
        return ""

    def _extract_filter_condition(self, node: ast.Call) -> str:
        """Extract filter condition as string"""
        if node.args:
            return ast.unparse(node.args[0]) if hasattr(ast, 'unparse') else str(node.args[0])
        return ""

    def _extract_columns(self, node: ast.Call) -> List[str]:
        """Extract column names from select/groupBy/orderBy"""
        columns = []
        for arg in node.args:
            if isinstance(arg, ast.Constant):
                columns.append(str(arg.value))
            elif isinstance(arg, ast.Name):
                columns.append(arg.id)
        return columns

    def _extract_join_type(self, node: ast.Call) -> str:
        """Extract join type from join() call"""
        for keyword in node.keywords:
            if keyword.arg == 'how' and isinstance(keyword.value, ast.Constant):
                return str(keyword.value.value)
        return "inner"

    def _extract_join_condition(self, node: ast.Call) -> str:
        """Extract join condition"""
        if len(node.args) >= 2:
            return ast.unparse(node.args[1]) if hasattr(ast, 'unparse') else str(node.args[1])
        return ""

    def _extract_dependencies(self, node: ast.AST) -> List[str]:
        """Extract variable dependencies from expression"""
        dependencies = []
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                dependencies.append(child.id)
        return dependencies


class CodeGenerator:
    """Generate code (Python/PySpark) from pipeline definition"""

    def generate_pyspark_code(self, pipeline: PipelineDefinition) -> str:
        """Generate PySpark code from pipeline definition"""
        code_lines = [
            "from pyspark.sql import SparkSession",
            "from pyspark.sql import functions as F",
            "",
            "# Initialize Spark session",
            "spark = SparkSession.builder.appName('NeuroLake Pipeline').getOrCreate()",
            ""
        ]

        # Build execution order from edges
        node_map = {node.id: node for node in pipeline.nodes}
        execution_order = self._topological_sort(pipeline.nodes, pipeline.edges)

        # Generate code for each node
        var_map = {}  # node_id -> variable_name
        var_counter = 0

        for node_id in execution_order:
            node = node_map[node_id]
            var_name = f"df_{var_counter}"
            var_counter += 1
            var_map[node_id] = var_name

            code = self._generate_node_code(node, var_name, pipeline.edges, var_map)
            if code:
                code_lines.append(code)
                code_lines.append("")

        return "\n".join(code_lines)

    def _generate_node_code(self, node: PipelineNode, var_name: str,
                           edges: List[PipelineEdge], var_map: Dict[str, str]) -> str:
        """Generate code for a single node"""
        config = node.config

        if node.type == NodeType.READ:
            source = config.get('source', 'unknown')
            source_type = config.get('source_type', 'table')

            if source_type == 'table':
                return f"{var_name} = spark.read.table('{source}')"
            elif source_type == 'parquet':
                return f"{var_name} = spark.read.parquet('{source}')"
            elif source_type == 'csv':
                return f"{var_name} = spark.read.csv('{source}', header=True, inferSchema=True)"

        elif node.type == NodeType.WRITE:
            # Find source node
            source_var = self._find_source_var(node.id, edges, var_map)
            target = config.get('target', 'output')
            mode = config.get('mode', 'overwrite')
            return f"{source_var}.write.mode('{mode}').saveAsTable('{target}')"

        elif node.type == NodeType.FILTER:
            source_var = self._find_source_var(node.id, edges, var_map)
            condition = config.get('condition', 'True')
            return f"{var_name} = {source_var}.filter({condition})"

        elif node.type == NodeType.SELECT:
            source_var = self._find_source_var(node.id, edges, var_map)
            columns = config.get('columns', [])
            cols_str = ", ".join([f"'{col}'" for col in columns])
            return f"{var_name} = {source_var}.select({cols_str})"

        elif node.type == NodeType.JOIN:
            # Find two source nodes
            sources = self._find_all_source_vars(node.id, edges, var_map)
            if len(sources) >= 2:
                join_type = config.get('join_type', 'inner')
                condition = config.get('condition', 'True')
                return f"{var_name} = {sources[0]}.join({sources[1]}, {condition}, '{join_type}')"

        elif node.type == NodeType.AGGREGATE:
            source_var = self._find_source_var(node.id, edges, var_map)
            group_by = config.get('group_by', [])
            agg_funcs = config.get('aggregations', [])

            group_cols = ", ".join([f"'{col}'" for col in group_by])
            agg_exprs = ", ".join([f"F.{agg['func']}('{agg['column']}').alias('{agg['alias']}')"
                                   for agg in agg_funcs])

            return f"{var_name} = {source_var}.groupBy({group_cols}).agg({agg_exprs})"

        elif node.type == NodeType.SORT:
            source_var = self._find_source_var(node.id, edges, var_map)
            columns = config.get('columns', [])
            cols_str = ", ".join([f"'{col}'" for col in columns])
            return f"{var_name} = {source_var}.orderBy({cols_str})"

        elif node.type == NodeType.UNION:
            sources = self._find_all_source_vars(node.id, edges, var_map)
            if len(sources) >= 2:
                union_chain = ".union(".join(sources) + ")" * (len(sources) - 1)
                return f"{var_name} = {union_chain}"

        return f"# {node.type.value} operation (config: {config})"

    def _topological_sort(self, nodes: List[PipelineNode],
                         edges: List[PipelineEdge]) -> List[str]:
        """Sort nodes in execution order"""
        # Build adjacency list
        adj = {node.id: [] for node in nodes}
        in_degree = {node.id: 0 for node in nodes}

        for edge in edges:
            adj[edge.source].append(edge.target)
            in_degree[edge.target] += 1

        # Find nodes with no incoming edges
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for neighbor in adj[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def _find_source_var(self, node_id: str, edges: List[PipelineEdge],
                        var_map: Dict[str, str]) -> str:
        """Find the source variable for a node"""
        for edge in edges:
            if edge.target == node_id:
                return var_map.get(edge.source, 'df')
        return 'df'

    def _find_all_source_vars(self, node_id: str, edges: List[PipelineEdge],
                             var_map: Dict[str, str]) -> List[str]:
        """Find all source variables for a node"""
        sources = []
        for edge in edges:
            if edge.target == node_id:
                sources.append(var_map.get(edge.source, 'df'))
        return sources


class PipelineCodeGenerator:
    """Main class for bi-directional pipeline-code synchronization"""

    def __init__(self):
        self.parser = CodeParser()
        self.generator = CodeGenerator()

    def json_to_code(self, pipeline_json: Dict, language: str = "pyspark") -> str:
        """Convert visual pipeline JSON to code"""
        # Parse JSON to PipelineDefinition
        pipeline = self._json_to_pipeline(pipeline_json)

        if language == "pyspark":
            return self.generator.generate_pyspark_code(pipeline)
        else:
            raise ValueError(f"Unsupported language: {language}")

    def code_to_json(self, code: str, language: str = "pyspark") -> Dict:
        """Convert code to visual pipeline JSON"""
        if language == "pyspark":
            pipeline = self.parser.parse_pyspark_code(code)
            return self._pipeline_to_json(pipeline)
        else:
            raise ValueError(f"Unsupported language: {language}")

    def _json_to_pipeline(self, json_data: Dict) -> PipelineDefinition:
        """Convert JSON to PipelineDefinition object"""
        nodes = [
            PipelineNode(
                id=n['id'],
                type=NodeType(n['type']),
                config=n.get('config', {}),
                position=n.get('position', {"x": 0, "y": 0}),
                metadata=n.get('metadata', {})
            )
            for n in json_data.get('nodes', [])
        ]

        edges = [
            PipelineEdge(
                id=e.get('id', f"edge_{i}"),
                source=e['from'] if 'from' in e else e['source'],
                target=e['to'] if 'to' in e else e['target'],
                source_port=e.get('source_port'),
                target_port=e.get('target_port')
            )
            for i, e in enumerate(json_data.get('edges', []))
        ]

        return PipelineDefinition(
            id=json_data.get('id', 'pipeline_1'),
            name=json_data.get('name', 'Untitled Pipeline'),
            nodes=nodes,
            edges=edges,
            metadata=json_data.get('metadata', {})
        )

    def _pipeline_to_json(self, pipeline: PipelineDefinition) -> Dict:
        """Convert PipelineDefinition to JSON"""
        return {
            'id': pipeline.id,
            'name': pipeline.name,
            'nodes': [
                {
                    'id': node.id,
                    'type': node.type.value,
                    'config': node.config,
                    'position': node.position,
                    'metadata': node.metadata
                }
                for node in pipeline.nodes
            ],
            'edges': [
                {
                    'id': edge.id,
                    'from': edge.source,
                    'to': edge.target,
                    'source_port': edge.source_port,
                    'target_port': edge.target_port
                }
                for edge in pipeline.edges
            ],
            'metadata': pipeline.metadata
        }

    def validate_pipeline(self, pipeline_json: Dict) -> Tuple[bool, List[str]]:
        """Validate pipeline structure and logic"""
        errors = []

        # Check required fields
        if 'nodes' not in pipeline_json:
            errors.append("Missing 'nodes' field")
        if 'edges' not in pipeline_json:
            errors.append("Missing 'edges' field")

        if errors:
            return False, errors

        # Validate nodes
        node_ids = set()
        for node in pipeline_json['nodes']:
            if 'id' not in node:
                errors.append("Node missing 'id' field")
            else:
                if node['id'] in node_ids:
                    errors.append(f"Duplicate node ID: {node['id']}")
                node_ids.add(node['id'])

            if 'type' not in node:
                errors.append(f"Node {node.get('id', 'unknown')} missing 'type' field")

        # Validate edges
        for edge in pipeline_json['edges']:
            source = edge.get('from') or edge.get('source')
            target = edge.get('to') or edge.get('target')

            if not source:
                errors.append("Edge missing source node")
            elif source not in node_ids:
                errors.append(f"Edge references non-existent source node: {source}")

            if not target:
                errors.append("Edge missing target node")
            elif target not in node_ids:
                errors.append(f"Edge references non-existent target node: {target}")

        # Check for cycles (optional - pipelines can have cycles in some cases)
        # For now, just validate structure

        return len(errors) == 0, errors