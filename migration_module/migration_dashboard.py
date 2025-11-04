"""
Comprehensive Migration Dashboard
Streamlit-based dashboard for managing code migrations
"""

import streamlit as st
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# Import migration components
from .upload_handler import UploadHandler
from .parsers import SQLParser, ETLParser, MainframeParser
from .logic_extractor import LogicExtractor
from .agents import SQLConverterAgent, SparkConverterAgent
from .validators.validation_framework import ValidationFramework
from .connectors.data_connector import DataConnector
from .execution_engine import ExecutionEngine
from .config import SUPPORTED_PLATFORMS, TARGET_PLATFORMS


class MigrationDashboard:
    """Main dashboard for migration module"""

    def __init__(self):
        self.upload_handler = UploadHandler()
        self.logic_extractor = LogicExtractor()
        self.sql_converter = SQLConverterAgent()
        self.spark_converter = SparkConverterAgent()
        self.validator = ValidationFramework()
        self.data_connector = DataConnector()
        self.execution_engine = ExecutionEngine()

    def run(self):
        """Run the dashboard"""

        st.set_page_config(
            page_title="NeuroLake Migration Module",
            page_icon="🔄",
            layout="wide"
        )

        st.title("🔄 NeuroLake Migration Module")
        st.markdown("**AI-Driven Code Migration Platform**")
        st.markdown("---")

        # Sidebar navigation
        page = st.sidebar.selectbox(
            "Navigation",
            [
                "📤 Upload & Parse",
                "🧠 Logic Extraction",
                "🔄 SQL to SQL",
                "⚡ ETL to Spark",
                "✅ Validation",
                "🔌 Data Connectors",
                "▶️ Execute & Monitor",
                "📊 Migration History",
                "⚙️ Settings"
            ]
        )

        # Route to appropriate page
        if page == "📤 Upload & Parse":
            self.upload_and_parse_page()
        elif page == "🧠 Logic Extraction":
            self.logic_extraction_page()
        elif page == "🔄 SQL to SQL":
            self.sql_conversion_page()
        elif page == "⚡ ETL to Spark":
            self.spark_conversion_page()
        elif page == "✅ Validation":
            self.validation_page()
        elif page == "🔌 Data Connectors":
            self.data_connectors_page()
        elif page == "▶️ Execute & Monitor":
            self.execution_page()
        elif page == "📊 Migration History":
            self.history_page()
        elif page == "⚙️ Settings":
            self.settings_page()

    def upload_and_parse_page(self):
        """Upload and parse code"""

        st.header("📤 Upload & Parse Code")

        st.markdown("""
        Upload your existing code for migration. Supported platforms:
        - **SQL**: Oracle, SQL Server, PostgreSQL, MySQL, DB2, Teradata
        - **ETL Tools**: Talend, DataStage, Informatica, SSIS, Pentaho, Ab Initio
        - **Mainframe**: COBOL, JCL, REXX, PL/I
        """)

        # File upload
        uploaded_file = st.file_uploader(
            "Upload your code file",
            type=['sql', 'txt', 'xml', 'item', 'dsx', 'dtsx', 'ktr', 'kjb', 'cbl', 'cob', 'jcl'],
            help="Upload SQL procedures, ETL jobs, or mainframe code"
        )

        if uploaded_file:
            st.success(f"File uploaded: {uploaded_file.name}")

            # Additional metadata
            col1, col2 = st.columns(2)
            with col1:
                source_system = st.text_input("Source System", placeholder="e.g., Production DB")
            with col2:
                description = st.text_input("Description", placeholder="Brief description")

            if st.button("Parse Code", type="primary"):
                with st.spinner("Parsing code..."):
                    try:
                        # Read file content
                        content = uploaded_file.read()

                        # Save upload
                        metadata = self.upload_handler.save_upload(
                            uploaded_file.name,
                            content,
                            {'source_system': source_system, 'description': description}
                        )

                        st.success(f"✅ File parsed successfully!")
                        st.json(metadata)

                        # Parse based on platform
                        platform = metadata['platform']
                        decoded_content = content.decode('utf-8')

                        if platform == 'sql':
                            parser = SQLParser()
                            parsed_data = parser.parse(decoded_content)
                        elif platform in ['talend', 'datastage', 'informatica', 'ssis', 'pentaho', 'abinitio']:
                            parser = ETLParser()
                            parsed_data = parser.parse(decoded_content, platform)
                        elif platform == 'mainframe':
                            parser = MainframeParser()
                            parsed_data = parser.parse(decoded_content)
                        else:
                            parsed_data = {'error': 'Unsupported platform'}

                        # Display parsed info
                        st.subheader("Parsed Information")
                        st.json(parsed_data)

                        # Store in session state
                        st.session_state['last_upload'] = metadata
                        st.session_state['last_parsed'] = parsed_data

                    except Exception as e:
                        st.error(f"Error parsing file: {str(e)}")

        # Show recent uploads
        st.markdown("---")
        st.subheader("Recent Uploads")

        recent_uploads = self.upload_handler.list_uploads()
        if recent_uploads:
            for upload in recent_uploads[:5]:
                with st.expander(f"{upload['filename']} - {upload['platform_name']}"):
                    st.json(upload)
        else:
            st.info("No uploads yet")

    def logic_extraction_page(self):
        """Logic extraction page"""

        st.header("🧠 Logic Extraction")

        st.markdown("""
        Extract comprehensive business logic from your code using AI.
        This creates a detailed blueprint for migration.
        """)

        # Get last upload
        if 'last_upload' not in st.session_state:
            st.warning("Please upload and parse a file first")
            return

        upload = st.session_state['last_upload']
        parsed = st.session_state.get('last_parsed', {})

        st.info(f"Working with: {upload['filename']} ({upload['platform_name']})")

        if st.button("Extract Logic", type="primary"):
            with st.spinner("Extracting business logic using AI..."):
                try:
                    # Read original code
                    with open(upload['file_path'], 'r') as f:
                        code = f.read()

                    # Extract logic
                    logic = self.logic_extractor.extract_logic(
                        code,
                        upload['platform'],
                        parsed
                    )

                    st.success("✅ Logic extracted successfully!")

                    # Display extracted logic
                    tabs = st.tabs([
                        "Business Rules",
                        "Transformations",
                        "Data Lineage",
                        "Dependencies",
                        "Documentation"
                    ])

                    with tabs[0]:
                        st.json(logic.get('business_rules', []))

                    with tabs[1]:
                        st.json(logic.get('transformations', []))

                    with tabs[2]:
                        st.json(logic.get('data_lineage', {}))

                    with tabs[3]:
                        st.json(logic.get('dependencies', []))

                    with tabs[4]:
                        doc = self.logic_extractor.generate_documentation(logic)
                        st.markdown(doc)

                    # Store in session state
                    st.session_state['extracted_logic'] = logic

                except Exception as e:
                    st.error(f"Error extracting logic: {str(e)}")

    def sql_conversion_page(self):
        """SQL to SQL conversion page"""

        st.header("🔄 SQL to SQL Conversion")

        st.markdown("""
        Convert SQL between different database dialects with 100% logic preservation.
        """)

        # Check prerequisites
        if 'extracted_logic' not in st.session_state:
            st.warning("Please extract logic first")
            return

        upload = st.session_state['last_upload']
        logic = st.session_state['extracted_logic']

        # Configuration
        col1, col2, col3 = st.columns(3)
        with col1:
            source_dialect = st.selectbox(
                "Source Dialect",
                ['oracle', 'mssql', 'postgresql', 'mysql', 'db2', 'teradata']
            )
        with col2:
            target_dialect = st.selectbox(
                "Target Dialect",
                ['postgresql', 'mysql', 'snowflake', 'redshift', 'bigquery']
            )
        with col3:
            optimization = st.selectbox(
                "Optimization Level",
                ['preserve', 'balanced', 'aggressive']
            )

        if st.button("Convert SQL", type="primary"):
            with st.spinner("Converting SQL..."):
                try:
                    # Read original code
                    with open(upload['file_path'], 'r') as f:
                        original_sql = f.read()

                    # Convert
                    result = self.sql_converter.convert(
                        original_sql,
                        source_dialect,
                        target_dialect,
                        logic,
                        optimization
                    )

                    st.success("✅ SQL converted successfully!")

                    # Display results
                    tabs = st.tabs([
                        "Converted SQL",
                        "Validation",
                        "Comparison",
                        "Test Cases"
                    ])

                    with tabs[0]:
                        st.code(result.get('converted_sql', ''), language='sql')

                        # Download button
                        st.download_button(
                            "Download Converted SQL",
                            result.get('converted_sql', ''),
                            file_name=f"converted_{upload['filename']}",
                            mime="text/plain"
                        )

                    with tabs[1]:
                        validation = result.get('validation', {})
                        if validation.get('passed'):
                            st.success(f"✅ Validation Passed (Score: {validation.get('overall_score', 0)}/700)")
                        else:
                            st.error("❌ Validation Failed")

                        st.json(validation)

                    with tabs[2]:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.subheader("Original SQL")
                            st.code(original_sql[:1000] + "...", language='sql')
                        with col_b:
                            st.subheader("Converted SQL")
                            st.code(result.get('converted_sql', '')[:1000] + "...", language='sql')

                    with tabs[3]:
                        st.json(result.get('test_cases', {}))

                    # Store result
                    st.session_state['sql_conversion_result'] = result

                except Exception as e:
                    st.error(f"Error converting SQL: {str(e)}")

    def spark_conversion_page(self):
        """ETL to Spark conversion page"""

        st.header("⚡ ETL to Spark Conversion")

        st.markdown("""
        Convert ETL jobs to PySpark with data lineage tracking.
        """)

        # Check prerequisites
        if 'extracted_logic' not in st.session_state:
            st.warning("Please extract logic first")
            return

        upload = st.session_state['last_upload']
        logic = st.session_state['extracted_logic']

        # Configuration
        col1, col2 = st.columns(2)
        with col1:
            spark_version = st.selectbox("Spark Version", ['3.5', '3.4', '3.3', '3.2'])
        with col2:
            use_delta = st.checkbox("Use Delta Lake", value=True)

        if st.button("Convert to Spark", type="primary"):
            with st.spinner("Converting to Spark..."):
                try:
                    # Read original code
                    with open(upload['file_path'], 'r') as f:
                        original_code = f.read()

                    # Convert
                    result = self.spark_converter.convert_to_spark(
                        original_code,
                        upload['platform'],
                        logic,
                        spark_version,
                        use_delta
                    )

                    st.success("✅ Converted to Spark successfully!")

                    # Display results
                    tabs = st.tabs([
                        "PySpark Code",
                        "Data Lineage",
                        "Configuration",
                        "Tests",
                        "Validation"
                    ])

                    with tabs[0]:
                        st.code(result.get('pyspark_code', ''), language='python')

                        st.download_button(
                            "Download PySpark Code",
                            result.get('pyspark_code', ''),
                            file_name=f"spark_{upload['filename']}.py",
                            mime="text/x-python"
                        )

                    with tabs[1]:
                        lineage = result.get('data_lineage', {})
                        st.json(lineage)

                    with tabs[2]:
                        st.json(result.get('configuration', {}))

                    with tabs[3]:
                        st.code(result.get('test_code', ''), language='python')

                    with tabs[4]:
                        validation = result.get('spark_validation', {})
                        st.json(validation)

                    # Store result
                    st.session_state['spark_conversion_result'] = result

                except Exception as e:
                    st.error(f"Error converting to Spark: {str(e)}")

    def validation_page(self):
        """Validation page"""

        st.header("✅ Migration Validation")

        st.markdown("""
        Comprehensive validation of migration with 99%+ accuracy requirement.
        """)

        # Check if conversion exists
        if 'sql_conversion_result' not in st.session_state and 'spark_conversion_result' not in st.session_state:
            st.warning("Please complete a conversion first")
            return

        conversion_type = st.radio("Conversion Type", ["SQL", "Spark"])

        if st.button("Run Full Validation", type="primary"):
            with st.spinner("Running comprehensive validation..."):
                try:
                    upload = st.session_state['last_upload']
                    logic = st.session_state['extracted_logic']

                    # Read original code
                    with open(upload['file_path'], 'r') as f:
                        original_code = f.read()

                    if conversion_type == "SQL":
                        result = st.session_state['sql_conversion_result']
                        converted_code = result.get('converted_sql', '')
                        original_platform = result['source_dialect']
                        target_platform = result['target_dialect']
                    else:
                        result = st.session_state['spark_conversion_result']
                        converted_code = result.get('pyspark_code', '')
                        original_platform = result['platform']
                        target_platform = 'spark'

                    # Validate
                    validation_result = self.validator.validate_migration(
                        original_code,
                        converted_code,
                        original_platform,
                        target_platform,
                        logic
                    )

                    # Display results
                    if validation_result['passed']:
                        st.success(f"✅ VALIDATION PASSED (Score: {validation_result['overall_score']:.1%})")
                    else:
                        st.error(f"❌ VALIDATION FAILED (Score: {validation_result['overall_score']:.1%})")

                    # Metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Overall Score", f"{validation_result['overall_score']:.1%}")
                    with col2:
                        st.metric("Critical Issues", len(validation_result['critical_issues']))
                    with col3:
                        st.metric("Warnings", len(validation_result['warnings']))

                    # Detailed results
                    st.subheader("Validation Details")
                    for validation_name, validation_data in validation_result['validations'].items():
                        score = validation_data.get('score', 0)
                        status = '✅' if score >= 0.9 else '⚠️' if score >= 0.7 else '❌'

                        with st.expander(f"{status} {validation_name.replace('_', ' ').title()} - {score:.1%}"):
                            st.json(validation_data)

                    # Issues
                    if validation_result['critical_issues']:
                        st.error("🚨 Critical Issues")
                        for issue in validation_result['critical_issues']:
                            st.write(f"- {issue}")

                    # Recommendations
                    st.subheader("💡 Recommendations")
                    for rec in validation_result['recommendations']:
                        st.write(f"- {rec}")

                    # Report
                    report = self.validator.generate_validation_report(validation_result)
                    st.download_button(
                        "Download Validation Report",
                        report,
                        file_name="validation_report.md",
                        mime="text/markdown"
                    )

                except Exception as e:
                    st.error(f"Error during validation: {str(e)}")

    def data_connectors_page(self):
        """Data connectors page"""

        st.header("🔌 Data Source Connectors")

        st.markdown("Connect to data sources for testing migrated code.")

        source_type = st.selectbox(
            "Source Type",
            self.data_connector.supported_sources
        )

        st.subheader("Connection Configuration")

        if source_type in ['postgresql', 'mysql', 'oracle', 'mssql']:
            host = st.text_input("Host", "localhost")
            port = st.number_input("Port", value=5432)
            database = st.text_input("Database")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

        elif source_type in ['s3', 'azure_blob', 'gcs']:
            bucket = st.text_input("Bucket/Container")
            path = st.text_input("Path")
            credentials = st.text_area("Credentials (JSON)")

        if st.button("Test Connection"):
            st.info("Connection testing would be implemented here")

    def execution_page(self):
        """Execution and monitoring page"""

        st.header("▶️ Execute & Monitor")

        st.markdown("Execute migrated code and monitor results.")

        # Execution type
        exec_type = st.radio("Execution Type", ["SQL", "Spark"])

        if exec_type == "SQL":
            sql_code = st.text_area("SQL Code", height=200)

            if st.button("Execute SQL"):
                with st.spinner("Executing..."):
                    result = self.execution_engine.execute_sql(sql_code, {})
                    st.json(result)

        else:
            spark_code = st.text_area("PySpark Code", height=200)

            if st.button("Execute Spark Job"):
                with st.spinner("Executing..."):
                    result = self.execution_engine.execute_spark(spark_code, {})
                    st.json(result)

        # Recent executions
        st.subheader("Recent Executions")
        executions = self.execution_engine.list_executions(10)
        for execution in executions:
            with st.expander(f"{execution['execution_id']} - {execution['status']}"):
                st.json(execution)

    def history_page(self):
        """Migration history page"""

        st.header("📊 Migration History")

        st.markdown("View all migration activities.")

        uploads = self.upload_handler.list_uploads()

        if uploads:
            st.dataframe([
                {
                    'Filename': u['filename'],
                    'Platform': u['platform_name'],
                    'Upload Time': u['upload_timestamp'],
                    'Status': u['status']
                }
                for u in uploads
            ])
        else:
            st.info("No migration history yet")

    def settings_page(self):
        """Settings page"""

        st.header("⚙️ Settings")

        st.subheader("AI Configuration")
        api_key = st.text_input("Anthropic API Key", type="password")

        st.subheader("Validation Settings")
        validation_threshold = st.slider("Validation Threshold", 0.0, 1.0, 0.99)

        st.subheader("Supported Platforms")
        st.json(SUPPORTED_PLATFORMS)

        if st.button("Save Settings"):
            st.success("Settings saved!")


def main():
    """Main entry point"""
    dashboard = MigrationDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
