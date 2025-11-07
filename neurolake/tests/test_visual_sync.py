"""
Unit tests for Visual Sync Layer
Tests bi-directional pipeline-code synchronization
"""

import pytest
import json
from neurolake.visual_sync import (
    PipelineCodeGenerator,
    PipelineNode,
    PipelineEdge,
    PipelineDefinition,
    NodeType,
    CodeParser,
    CodeGenerator
)


class TestCodeParser:
    """Test code parsing functionality"""

    def test_parse_simple_read(self):
        """Test parsing simple read operation"""
        code = """
df = spark.read.table('customers')
"""
        parser = CodeParser()
        pipeline = parser.parse_pyspark_code(code)

        assert len(pipeline.nodes) == 1
        assert pipeline.nodes[0].type == NodeType.READ
        assert pipeline.nodes[0].config['source'] == 'customers'
        assert pipeline.nodes[0].config['source_type'] == 'table'

    def test_parse_filter_operation(self):
        """Test parsing filter operation"""
        code = """
df = spark.read.table('customers')
df_filtered = df.filter(df.age > 18)
"""
        parser = CodeParser()
        pipeline = parser.parse_pyspark_code(code)

        assert len(pipeline.nodes) == 2
        assert pipeline.nodes[1].type == NodeType.FILTER
        assert 'age' in pipeline.nodes[1].config['condition']

    def test_parse_select_operation(self):
        """Test parsing select operation"""
        code = """
df = spark.read.table('customers')
df_selected = df.select('name', 'email')
"""
        parser = CodeParser()
        pipeline = parser.parse_pyspark_code(code)

        assert len(pipeline.nodes) == 2
        assert pipeline.nodes[1].type == NodeType.SELECT
        assert 'name' in pipeline.nodes[1].config['columns']
        assert 'email' in pipeline.nodes[1].config['columns']

    def test_parse_write_operation(self):
        """Test parsing write operation"""
        code = """
df = spark.read.table('customers')
df.write.saveAsTable('customers_copy')
"""
        parser = CodeParser()
        pipeline = parser.parse_pyspark_code(code)

        assert len(pipeline.nodes) == 2
        assert pipeline.nodes[1].type == NodeType.WRITE
        assert pipeline.nodes[1].config['target'] == 'customers_copy'

    def test_parse_edges_from_dependencies(self):
        """Test that edges are correctly extracted from variable dependencies"""
        code = """
df1 = spark.read.table('table1')
df2 = df1.filter(df1.age > 18)
"""
        parser = CodeParser()
        pipeline = parser.parse_pyspark_code(code)

        assert len(pipeline.edges) == 1
        assert pipeline.edges[0].source == pipeline.nodes[0].id
        assert pipeline.edges[0].target == pipeline.nodes[1].id


class TestCodeGenerator:
    """Test code generation functionality"""

    def test_generate_simple_read(self):
        """Test generating read operation code"""
        nodes = [
            PipelineNode(
                id="node_0",
                type=NodeType.READ,
                config={"source": "customers", "source_type": "table"}
            )
        ]
        pipeline = PipelineDefinition(
            id="test_pipeline",
            name="Test",
            nodes=nodes,
            edges=[]
        )

        generator = CodeGenerator()
        code = generator.generate_pyspark_code(pipeline)

        assert "spark.read.table('customers')" in code
        assert "df_0" in code

    def test_generate_filter_operation(self):
        """Test generating filter operation code"""
        nodes = [
            PipelineNode(
                id="node_0",
                type=NodeType.READ,
                config={"source": "customers", "source_type": "table"}
            ),
            PipelineNode(
                id="node_1",
                type=NodeType.FILTER,
                config={"condition": "df.age > 18"}
            )
        ]
        edges = [
            PipelineEdge(id="edge_0", source="node_0", target="node_1")
        ]
        pipeline = PipelineDefinition(
            id="test_pipeline",
            name="Test",
            nodes=nodes,
            edges=edges
        )

        generator = CodeGenerator()
        code = generator.generate_pyspark_code(pipeline)

        assert ".filter(" in code
        assert "age > 18" in code

    def test_generate_write_operation(self):
        """Test generating write operation code"""
        nodes = [
            PipelineNode(
                id="node_0",
                type=NodeType.READ,
                config={"source": "customers", "source_type": "table"}
            ),
            PipelineNode(
                id="node_1",
                type=NodeType.WRITE,
                config={"target": "output_table", "mode": "overwrite"}
            )
        ]
        edges = [
            PipelineEdge(id="edge_0", source="node_0", target="node_1")
        ]
        pipeline = PipelineDefinition(
            id="test_pipeline",
            name="Test",
            nodes=nodes,
            edges=edges
        )

        generator = CodeGenerator()
        code = generator.generate_pyspark_code(pipeline)

        assert ".write.mode('overwrite').saveAsTable('output_table')" in code

    def test_topological_sort(self):
        """Test topological sorting of nodes"""
        nodes = [
            PipelineNode(id="node_0", type=NodeType.READ, config={}),
            PipelineNode(id="node_1", type=NodeType.FILTER, config={}),
            PipelineNode(id="node_2", type=NodeType.WRITE, config={})
        ]
        edges = [
            PipelineEdge(id="edge_0", source="node_0", target="node_1"),
            PipelineEdge(id="edge_1", source="node_1", target="node_2")
        ]

        generator = CodeGenerator()
        order = generator._topological_sort(nodes, edges)

        assert order.index("node_0") < order.index("node_1")
        assert order.index("node_1") < order.index("node_2")


class TestPipelineCodeGenerator:
    """Test the main PipelineCodeGenerator class"""

    def test_json_to_code_simple_pipeline(self):
        """Test converting simple JSON pipeline to code"""
        pipeline_json = {
            "id": "pipeline_1",
            "name": "Test Pipeline",
            "nodes": [
                {
                    "id": "1",
                    "type": "read",
                    "config": {"source": "customers", "source_type": "table"}
                },
                {
                    "id": "2",
                    "type": "filter",
                    "config": {"condition": "age > 18"}
                },
                {
                    "id": "3",
                    "type": "write",
                    "config": {"target": "adult_customers", "mode": "overwrite"}
                }
            ],
            "edges": [
                {"from": "1", "to": "2"},
                {"from": "2", "to": "3"}
            ]
        }

        generator = PipelineCodeGenerator()
        code = generator.json_to_code(pipeline_json, "pyspark")

        assert "spark.read.table('customers')" in code
        assert ".filter(age > 18)" in code
        assert ".saveAsTable('adult_customers')" in code

    def test_code_to_json_simple_pipeline(self):
        """Test converting simple code to JSON pipeline"""
        code = """
df = spark.read.table('customers')
df_filtered = df.filter(df.age > 18)
df_filtered.write.saveAsTable('adult_customers')
"""

        generator = PipelineCodeGenerator()
        pipeline_json = generator.code_to_json(code, "pyspark")

        assert len(pipeline_json['nodes']) == 3
        assert pipeline_json['nodes'][0]['type'] == 'read'
        assert pipeline_json['nodes'][1]['type'] == 'filter'
        assert pipeline_json['nodes'][2]['type'] == 'write'

    def test_validate_pipeline_valid(self):
        """Test validation of valid pipeline"""
        pipeline_json = {
            "nodes": [
                {"id": "1", "type": "read", "config": {}},
                {"id": "2", "type": "filter", "config": {}}
            ],
            "edges": [
                {"from": "1", "to": "2"}
            ]
        }

        generator = PipelineCodeGenerator()
        valid, errors = generator.validate_pipeline(pipeline_json)

        assert valid is True
        assert len(errors) == 0

    def test_validate_pipeline_missing_nodes(self):
        """Test validation with missing nodes field"""
        pipeline_json = {
            "edges": []
        }

        generator = PipelineCodeGenerator()
        valid, errors = generator.validate_pipeline(pipeline_json)

        assert valid is False
        assert "Missing 'nodes' field" in errors

    def test_validate_pipeline_invalid_edge_reference(self):
        """Test validation with invalid edge reference"""
        pipeline_json = {
            "nodes": [
                {"id": "1", "type": "read", "config": {}}
            ],
            "edges": [
                {"from": "1", "to": "999"}  # Non-existent target
            ]
        }

        generator = PipelineCodeGenerator()
        valid, errors = generator.validate_pipeline(pipeline_json)

        assert valid is False
        assert any("non-existent" in error.lower() for error in errors)

    def test_validate_pipeline_duplicate_node_ids(self):
        """Test validation with duplicate node IDs"""
        pipeline_json = {
            "nodes": [
                {"id": "1", "type": "read", "config": {}},
                {"id": "1", "type": "filter", "config": {}}  # Duplicate ID
            ],
            "edges": []
        }

        generator = PipelineCodeGenerator()
        valid, errors = generator.validate_pipeline(pipeline_json)

        assert valid is False
        assert any("Duplicate node ID" in error for error in errors)

    def test_round_trip_conversion(self):
        """Test round-trip: JSON -> Code -> JSON"""
        original_json = {
            "id": "pipeline_1",
            "name": "Test Pipeline",
            "nodes": [
                {
                    "id": "1",
                    "type": "read",
                    "config": {"source": "test_table", "source_type": "table"}
                },
                {
                    "id": "2",
                    "type": "filter",
                    "config": {"condition": "value > 100"}
                }
            ],
            "edges": [
                {"from": "1", "to": "2"}
            ]
        }

        generator = PipelineCodeGenerator()

        # JSON -> Code
        code = generator.json_to_code(original_json, "pyspark")

        # Code -> JSON
        result_json = generator.code_to_json(code, "pyspark")

        # Verify structure is preserved
        assert len(result_json['nodes']) == len(original_json['nodes'])
        assert result_json['nodes'][0]['type'] == 'read'
        assert result_json['nodes'][1]['type'] == 'filter'


class TestComplexPipelines:
    """Test complex pipeline scenarios"""

    def test_join_operation(self):
        """Test join operation code generation"""
        pipeline_json = {
            "nodes": [
                {"id": "1", "type": "read", "config": {"source": "customers", "source_type": "table"}},
                {"id": "2", "type": "read", "config": {"source": "orders", "source_type": "table"}},
                {
                    "id": "3",
                    "type": "join",
                    "config": {
                        "join_type": "inner",
                        "condition": "customers.id == orders.customer_id"
                    }
                }
            ],
            "edges": [
                {"from": "1", "to": "3"},
                {"from": "2", "to": "3"}
            ]
        }

        generator = PipelineCodeGenerator()
        code = generator.json_to_code(pipeline_json, "pyspark")

        assert ".join(" in code
        assert "'inner'" in code

    def test_aggregate_operation(self):
        """Test aggregate operation code generation"""
        pipeline_json = {
            "nodes": [
                {"id": "1", "type": "read", "config": {"source": "sales", "source_type": "table"}},
                {
                    "id": "2",
                    "type": "aggregate",
                    "config": {
                        "group_by": ["category", "region"],
                        "aggregations": [
                            {"func": "sum", "column": "amount", "alias": "total_amount"},
                            {"func": "count", "column": "*", "alias": "count"}
                        ]
                    }
                }
            ],
            "edges": [
                {"from": "1", "to": "2"}
            ]
        }

        generator = PipelineCodeGenerator()
        code = generator.json_to_code(pipeline_json, "pyspark")

        assert ".groupBy(" in code
        assert ".agg(" in code
        assert "category" in code
        assert "region" in code

    def test_multi_source_pipeline(self):
        """Test pipeline with multiple data sources"""
        pipeline_json = {
            "nodes": [
                {"id": "1", "type": "read", "config": {"source": "table1", "source_type": "table"}},
                {"id": "2", "type": "read", "config": {"source": "table2", "source_type": "table"}},
                {"id": "3", "type": "read", "config": {"source": "table3", "source_type": "table"}},
                {"id": "4", "type": "union", "config": {}},
                {"id": "5", "type": "write", "config": {"target": "combined", "mode": "overwrite"}}
            ],
            "edges": [
                {"from": "1", "to": "4"},
                {"from": "2", "to": "4"},
                {"from": "3", "to": "4"},
                {"from": "4", "to": "5"}
            ]
        }

        generator = PipelineCodeGenerator()
        code = generator.json_to_code(pipeline_json, "pyspark")

        assert code.count("spark.read.table") == 3
        assert ".union(" in code


if __name__ == '__main__':
    pytest.main([__file__, '-v'])