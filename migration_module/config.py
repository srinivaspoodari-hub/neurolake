"""
Migration Module Configuration
Supports all major ETL tools and platforms including mainframes
"""

import os
from typing import Dict, List

# Supported source platforms
SUPPORTED_PLATFORMS = {
    'sql': {
        'name': 'SQL Stored Procedures',
        'extensions': ['.sql', '.ddl', '.dml', '.rs'],
        'dialects': ['oracle', 'mssql', 'postgresql', 'mysql', 'db2', 'teradata', 'snowflake', 'rust_sql']
    },
    'talend': {
        'name': 'Talend',
        'extensions': ['.item', '.properties', '.xml'],
        'versions': ['7.x', '8.x']
    },
    'datastage': {
        'name': 'IBM DataStage',
        'extensions': ['.dsx', '.pjb', '.isx'],
        'versions': ['11.x', '11.5', '11.7']
    },
    'informatica': {
        'name': 'Informatica PowerCenter',
        'extensions': ['.xml', '.pmrep', '.rep'],
        'versions': ['10.x', 'IICS']
    },
    'mainframe': {
        'name': 'Mainframe (COBOL/JCL)',
        'extensions': ['.cbl', '.cob', '.jcl', '.proc', '.prc'],
        'languages': ['cobol', 'jcl', 'rexx', 'pl1']
    },
    'ssis': {
        'name': 'Microsoft SSIS',
        'extensions': ['.dtsx', '.dtproj'],
        'versions': ['2016', '2017', '2019', '2022']
    },
    'abinitio': {
        'name': 'Ab Initio',
        'extensions': ['.mp', '.mfs', '.dml'],
        'versions': ['3.x', '4.x']
    },
    'pentaho': {
        'name': 'Pentaho Data Integration',
        'extensions': ['.ktr', '.kjb'],
        'versions': ['8.x', '9.x']
    },
    'obiee': {
        'name': 'Oracle BI',
        'extensions': ['.rpd', '.xml'],
        'versions': ['12c']
    },
    'sap_bods': {
        'name': 'SAP Data Services (BODS)',
        'extensions': ['.atl', '.xml', '.dsx'],
        'versions': ['4.x']
    },
    'odi': {
        'name': 'Oracle Data Integrator (ODI)',
        'extensions': ['.xml', '.scen'],
        'versions': ['11g', '12c']
    },
    'sas': {
        'name': 'SAS ETL Studio / Data Integration',
        'extensions': ['.sas', '.egp', '.xml'],
        'versions': ['9.x']
    },
    'infosphere': {
        'name': 'IBM InfoSphere Information Server',
        'extensions': ['.isx', '.xml'],
        'versions': ['11.x']
    },
    'alteryx': {
        'name': 'Alteryx Designer',
        'extensions': ['.yxmd', '.yxwz', '.xml'],
        'versions': ['2020.x', '2021.x', '2022.x', '2023.x']
    },
    'snaplogic': {
        'name': 'SnapLogic',
        'extensions': ['.slp', '.json'],
        'versions': ['Enterprise']
    },
    'matillion': {
        'name': 'Matillion ETL',
        'extensions': ['.json', '.zip'],
        'versions': ['1.x']
    },
    'adf': {
        'name': 'Azure Data Factory (Legacy)',
        'extensions': ['.json'],
        'versions': ['V1', 'V2']
    },
    'glue': {
        'name': 'AWS Glue ETL',
        'extensions': ['.py', '.scala', '.json'],
        'versions': ['1.0', '2.0', '3.0', '4.0']
    },
    'nifi': {
        'name': 'Apache NiFi',
        'extensions': ['.xml', '.json'],
        'versions': ['1.x']
    },
    'airflow': {
        'name': 'Apache Airflow DAGs',
        'extensions': ['.py'],
        'versions': ['1.x', '2.x']
    },
    'streamsets': {
        'name': 'StreamSets Data Collector',
        'extensions': ['.json'],
        'versions': ['3.x', '4.x', '5.x']
    }
}

# Target platforms
TARGET_PLATFORMS = {
    'sql': {
        'name': 'Optimized SQL',
        'engines': ['postgresql', 'mysql', 'snowflake', 'redshift', 'bigquery', 'rust_sql']
    },
    'spark': {
        'name': 'Apache Spark (PySpark)',
        'versions': ['3.0', '3.1', '3.2', '3.3', '3.4', '3.5']
    },
    'databricks': {
        'name': 'Databricks SQL & Delta',
        'features': ['delta_lake', 'photon', 'serverless']
    },
    'neurolake': {
        'name': 'NeuroLake Platform',
        'storage_formats': ['ncf', 'delta_lake', 'parquet', 'iceberg'],
        'features': ['ai_native', 'auto_optimization', 'intelligent_caching', 'ml_integration'],
        'query_engines': ['neurolake_sql', 'spark', 'presto', 'rust_sql']
    }
}

# AI Model Configuration
AI_CONFIG = {
    'code_parser': {
        'model': 'claude-sonnet-4',
        'temperature': 0.1,
        'max_tokens': 8000
    },
    'logic_extractor': {
        'model': 'claude-sonnet-4',
        'temperature': 0.0,
        'max_tokens': 16000
    },
    'code_generator': {
        'model': 'claude-opus-4',
        'temperature': 0.0,
        'max_tokens': 32000
    },
    'validator': {
        'model': 'claude-sonnet-4',
        'temperature': 0.0,
        'max_tokens': 16000
    }
}

# Migration Settings
MIGRATION_SETTINGS = {
    'max_file_size_mb': 100,
    'batch_size': 10,
    'enable_validation': True,
    'enable_testing': True,
    'preserve_comments': True,
    'optimize_code': True,
    'generate_documentation': True,
    'create_test_data': True,
    'validate_logic_100_percent': True
}

# Upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Conversion rules
CONVERSION_RULES = {
    'sql_to_sql': {
        'preserve_logic': True,
        'optimize_joins': True,
        'add_error_handling': True,
        'modernize_syntax': True
    },
    'etl_to_spark': {
        'use_dataframes': True,
        'enable_catalyst_optimizer': True,
        'partition_strategy': 'auto',
        'cache_intermediate': True,
        'broadcast_small_tables': True
    },
    'mainframe_to_modern': {
        'convert_cobol_to_python': True,
        'convert_jcl_to_airflow': True,
        'preserve_business_logic': True,
        'modernize_file_handling': True
    }
}
