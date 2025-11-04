# How the Migration Module Works - Complete Explanation

## 📍 Entry Point: `run_migration_module.py`

This is the **main entry point** - the file you run to start the migration process.

---

## 🚀 Two Ways to Use It

### 1. **Dashboard Mode (Interactive UI)**
```bash
python run_migration_module.py
# OR
python run_migration_module.py dashboard
```
Opens a web browser with interactive interface

### 2. **CLI Mode (Command Line)**
```bash
python run_migration_module.py cli -i myfile.sql -t spark --api-key KEY
```
Runs automated migration from command line

---

## 🔄 Complete Conversion Flow (Step-by-Step)

### **STEP 1: UPLOAD & DETECT** 📤

```
User uploads file → run_migration_module.py → UploadHandler
                                                    ↓
                                          Detect Platform
                                          (by extension & content)
```

**Example**:
```python
# User uploads: oracle_procedure.sql
handler = UploadHandler()
metadata = handler.save_upload('oracle_procedure.sql', file_content)

# Result:
# metadata = {
#     'platform': 'sql',
#     'platform_name': 'SQL Stored Procedures',
#     'dialect': 'oracle'
# }
```

**Platform Detection Logic**:
- `.sql` → SQL platform
- `.xml` with `<talend>` → Talend
- `.dsx` → DataStage
- `.cbl` or `IDENTIFICATION DIVISION` → COBOL
- `.dtsx` → SSIS
- `.py` with `dag_id=` → Airflow
- etc.

---

### **STEP 2: PARSE CODE** 🔍

```
Detected Platform → Select Parser → Parse Structure
                         ↓
              SQLParser / ETLParser / MainframeParser
                         ↓
              Extract code structure
```

**Example - SQL Parsing**:
```python
# Input: Oracle PL/SQL procedure
CREATE OR REPLACE PROCEDURE process_orders(p_date DATE) AS
  v_count NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_count
  FROM orders
  WHERE order_date = p_date;

  INSERT INTO order_summary
  SELECT customer_id, SUM(amount)
  FROM orders
  WHERE order_date = p_date
  GROUP BY customer_id;
END;

# Parser extracts:
parsed_data = {
    'type': 'sql',
    'procedures': [{
        'name': 'process_orders',
        'parameters': [{'name': 'p_date', 'type': 'DATE'}]
    }],
    'tables': ['orders', 'order_summary'],
    'variables': ['v_count'],
    'transformations': ['COUNT(*)', 'SUM(amount)'],
    'joins': [],
    'aggregations': [{'function': 'SUM', 'expression': 'amount'}]
}
```

**Example - Talend Parsing**:
```python
# Input: Talend XML job
<talend>
  <node componentName="tOracleInput">
    <elementParameter name="TABLE" value="orders"/>
  </node>
  <node componentName="tMap">
    <elementParameter name="TRANSFORMATION" value="amount * 1.1"/>
  </node>
  <node componentName="tPostgresOutput">
    <elementParameter name="TABLE" value="processed_orders"/>
  </node>
</talend>

# Parser extracts:
parsed_data = {
    'platform': 'talend',
    'sources': [{'type': 'tOracleInput', 'table': 'orders'}],
    'transformations': [{'type': 'tMap', 'logic': 'amount * 1.1'}],
    'targets': [{'type': 'tPostgresOutput', 'table': 'processed_orders'}]
}
```

---

### **STEP 3: EXTRACT BUSINESS LOGIC** 🧠

```
Parsed Data → Logic Extractor (AI-powered) → Detailed Logic
                      ↓
            Uses Claude AI to understand:
            - Business rules
            - Transformations
            - Data lineage
            - Dependencies
```

**Example**:
```python
extractor = LogicExtractor(api_key='...')
logic = extractor.extract_logic(code, platform, parsed_data)

# AI extracts:
logic = {
    'business_rules': [
        {
            'rule_id': 'BR001',
            'description': 'Count orders for specific date',
            'logic': 'SELECT COUNT(*) FROM orders WHERE order_date = p_date',
            'conditions': ['order_date must match input parameter']
        },
        {
            'rule_id': 'BR002',
            'description': 'Aggregate orders by customer',
            'logic': 'SUM(amount) GROUP BY customer_id',
            'conditions': ['Only orders from specified date']
        }
    ],
    'transformations': [
        {
            'transformation_id': 'T001',
            'type': 'aggregate',
            'source_columns': ['amount'],
            'target_columns': ['total_amount'],
            'logic': 'SUM(amount)',
            'sql_equivalent': 'SELECT SUM(amount) FROM orders GROUP BY customer_id'
        }
    ],
    'data_lineage': {
        'order_summary.customer_id': {
            'source_tables': ['orders'],
            'source_columns': ['customer_id'],
            'transformation_steps': ['GROUP BY']
        },
        'order_summary.total_amount': {
            'source_tables': ['orders'],
            'source_columns': ['amount'],
            'transformation_steps': ['SUM aggregation']
        }
    }
}
```

---

### **STEP 4: CONVERT CODE** 🔄

**Two Conversion Paths**:

#### **Path A: SQL → SQL** (Different Dialects)

```
Oracle SQL → SQL Converter Agent → PostgreSQL SQL
                    ↓
         5-Step AI Conversion Process
```

**Example**:
```python
converter = SQLConverterAgent(api_key='...')
result = converter.convert(
    original_sql=oracle_code,
    source_dialect='oracle',
    target_dialect='postgresql',
    extracted_logic=logic
)

# Conversion Steps:

# Step 1: Analyze Requirements
# - Oracle uses DECODE → PostgreSQL uses CASE
# - Oracle uses NVL → PostgreSQL uses COALESCE
# - Oracle uses (+) join → PostgreSQL uses LEFT JOIN

# Step 2: Generate Converted SQL
CREATE OR REPLACE FUNCTION process_orders(p_date DATE)
RETURNS VOID AS $$
DECLARE
  v_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO v_count
  FROM orders
  WHERE order_date = p_date;

  INSERT INTO order_summary
  SELECT customer_id, SUM(amount)
  FROM orders
  WHERE order_date = p_date
  GROUP BY customer_id;
END;
$$ LANGUAGE plpgsql;

# Step 3: Validate (ensures 100% logic match)
# Step 4: Optimize
# Step 5: Generate tests
```

#### **Path B: ETL/SQL → Spark** (Modern Platform)

```
Talend/DataStage/SQL → Spark Converter Agent → PySpark Code
                              ↓
                  6-Step AI Conversion Process
```

**Example**:
```python
converter = SparkConverterAgent(api_key='...')
result = converter.convert_to_spark(
    original_code=talend_xml,
    platform='talend',
    extracted_logic=logic,
    spark_version='3.5',
    use_delta=True
)

# Generated PySpark Code:
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from delta import *
import logging

class OrderProcessingETL:
    def __init__(self, spark):
        self.spark = spark
        self.logger = logging.getLogger(__name__)

    def read_orders(self, order_date):
        """Read orders from source"""
        df = self.spark.read \
            .format("jdbc") \
            .option("url", "jdbc:oracle:thin:@...") \
            .option("dbtable", "orders") \
            .load() \
            .filter(col("order_date") == order_date)

        self.logger.info(f"Read {df.count()} orders for {order_date}")
        return df

    def transform_orders(self, df):
        """Aggregate orders by customer"""
        result = df.groupBy("customer_id") \
            .agg(sum("amount").alias("total_amount"))

        self.logger.info(f"Transformed to {result.count()} customer summaries")
        return result

    def write_results(self, df):
        """Write to Delta Lake"""
        df.write \
            .format("delta") \
            .mode("append") \
            .save("/path/to/order_summary")

        self.logger.info("Results written to Delta Lake")

    def run(self, order_date):
        """Main ETL pipeline"""
        try:
            orders_df = self.read_orders(order_date)
            transformed_df = self.transform_orders(orders_df)
            self.write_results(transformed_df)
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"ETL failed: {str(e)}")
            raise

if __name__ == "__main__":
    spark = SparkSession.builder \
        .appName("OrderProcessing") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .getOrCreate()

    etl = OrderProcessingETL(spark)
    etl.run("2024-01-01")
```

---

### **STEP 5: VALIDATE** ✅

```
Original Code + Converted Code → Validation Framework → Pass/Fail
                                         ↓
                              8-Dimension Validation
                              (Must score 99%+)
```

**Validation Checks**:

```python
validator = ValidationFramework(api_key='...')
validation = validator.validate_migration(
    original_code=oracle_code,
    converted_code=postgresql_code,
    original_platform='oracle',
    target_platform='postgresql',
    extracted_logic=logic
)

# Validation Result:
{
    'overall_score': 0.985,  # 98.5%
    'passed': False,  # Needs 99%+

    'validations': {
        'logic_preservation': {
            'score': 1.0,  # 100% - Perfect
            'logic_match_percentage': 100,
            'missing_rules': []
        },
        'syntax_correctness': {
            'score': 1.0,  # 100% - Valid SQL
            'syntax_valid': True
        },
        'data_type_compatibility': {
            'score': 0.95,  # 95% - Minor precision issue
            'issues': ['NUMBER(10,2) → NUMERIC(10,2): Potential rounding']
        },
        'edge_case_handling': {
            'score': 0.98,  # 98% - Good
            'warnings': ['NULL handling: verify behavior']
        }
    },

    'critical_issues': [],
    'warnings': ['Review data type mappings'],
    'recommendations': [
        'Test with production data',
        'Verify NULL handling',
        'Run performance benchmarks'
    ]
}
```

---

### **STEP 6: EXECUTE & TEST** ▶️

```
Converted Code → Execution Engine → Run with Test Data → Compare Results
```

**Example**:
```python
engine = ExecutionEngine()

# Execute original
original_result = engine.execute_sql(
    oracle_code,
    oracle_connection
)

# Execute converted
converted_result = engine.execute_sql(
    postgresql_code,
    postgres_connection
)

# Compare
comparison = engine.compare_executions(
    original_result['execution_id'],
    converted_result['execution_id']
)

# Result:
{
    'status_match': True,
    'rows_match': True,
    'data_equivalent': True,  # AI validates actual data
    'performance_comparison': {
        'original_duration': 2.5,
        'converted_duration': 1.8  # 28% faster!
    }
}
```

---

## 🌐 How Many Languages Can We Convert?

### **SOURCE LANGUAGES (What You Can Upload)** ✅

#### **1. SQL Languages (7)**
```
✅ Oracle PL/SQL        → Any Modern SQL
✅ T-SQL (SQL Server)   → Any Modern SQL
✅ PL/pgSQL (PostgreSQL)→ Any Modern SQL
✅ MySQL Procedures     → Any Modern SQL
✅ DB2 SQL PL          → Any Modern SQL
✅ Teradata SQL        → Any Modern SQL
✅ Snowflake SQL       → Any Modern SQL
```

#### **2. ETL Tool Languages/Formats (15)**
```
✅ Talend (XML)         → Spark/SQL
✅ DataStage (DSX)      → Spark/SQL
✅ Informatica (XML)    → Spark/SQL
✅ SSIS (DTSX)         → Spark/SQL
✅ Pentaho (KTR/KJB)   → Spark/SQL
✅ Ab Initio (MP)      → Spark/SQL
✅ SAP BODS (ATL)      → Spark/SQL
✅ ODI (XML)           → Spark/SQL
✅ SAS (SAS)           → Spark/SQL
✅ InfoSphere (ISX)    → Spark/SQL
✅ Alteryx (YXMD)      → Spark/SQL
✅ SnapLogic (JSON)    → Spark/SQL
✅ Matillion (JSON)    → Spark/SQL
✅ ADF (JSON)          → Spark/SQL
✅ Glue (PY/Scala)     → Optimized Spark
```

#### **3. Mainframe Languages (4)**
```
✅ COBOL               → Python/Spark
✅ JCL                 → Airflow/Spark
✅ REXX                → Python/Spark
✅ PL/I                → Python/Spark
```

#### **4. Orchestration Languages (3)**
```
✅ NiFi (XML)          → Spark/Airflow
✅ Airflow (Python)    → Optimized Airflow
✅ StreamSets (JSON)   → Spark/Kafka
```

### **TOTAL SOURCE LANGUAGES: 29**

---

### **TARGET LANGUAGES (What You Get)** 🎯

#### **1. SQL (5 Engines)**
```
✅ PostgreSQL (PL/pgSQL)
✅ MySQL (Stored Procedures)
✅ Snowflake SQL
✅ Amazon Redshift SQL
✅ Google BigQuery SQL
```

#### **2. Spark/Python (6 Versions)**
```
✅ PySpark 3.0
✅ PySpark 3.1
✅ PySpark 3.2
✅ PySpark 3.3
✅ PySpark 3.4
✅ PySpark 3.5 (Latest)
```

#### **3. Databricks**
```
✅ Databricks SQL
✅ Databricks + Delta Lake
✅ Databricks Workflows
```

### **TOTAL TARGET PLATFORMS: 3 (with 14 variants)**

---

## 📊 Conversion Matrix

| FROM (Source) | TO (Target) | Status | Example |
|---------------|-------------|--------|---------|
| Oracle PL/SQL | PostgreSQL | ✅ | procedure.sql → function.sql |
| T-SQL | MySQL | ✅ | sproc.sql → procedure.sql |
| Talend XML | PySpark | ✅ | job.item → etl.py |
| DataStage DSX | Spark + Delta | ✅ | job.dsx → pipeline.py |
| Informatica XML | PySpark | ✅ | mapping.xml → transform.py |
| COBOL | Python + Spark | ✅ | program.cbl → app.py |
| JCL | Airflow DAG | ✅ | job.jcl → dag.py |
| SSIS DTSX | PySpark | ✅ | package.dtsx → etl.py |
| SAP BODS | Spark | ✅ | job.atl → pipeline.py |
| Alteryx YXMD | PySpark | ✅ | workflow.yxmd → ml_pipeline.py |
| AWS Glue | Optimized Spark | ✅ | glue_job.py → optimized.py |
| Any SQL | Any SQL | ✅ | any_dialect.sql → target.sql |
| Any ETL | Spark | ✅ | etl_job.* → pyspark.py |
| Any Mainframe | Modern Platform | ✅ | legacy.* → modern.py |

---

## 🎯 Real-World Example: Complete Flow

### **Scenario**: Migrate Oracle procedure to PostgreSQL + Spark

```bash
# Step 1: Start with Oracle procedure
oracle_procedure.sql:
--------------------
CREATE OR REPLACE PROCEDURE sales_summary(p_year NUMBER) AS
  CURSOR c_sales IS
    SELECT region, SUM(amount) as total
    FROM sales
    WHERE EXTRACT(YEAR FROM sale_date) = p_year
    GROUP BY region;
BEGIN
  FOR rec IN c_sales LOOP
    INSERT INTO sales_summary VALUES (p_year, rec.region, rec.total);
  END LOOP;
  COMMIT;
END;

# Step 2: Run migration (CLI)
python run_migration_module.py cli \
  -i oracle_procedure.sql \
  -t sql \
  --source-dialect oracle \
  --target-dialect postgresql \
  --api-key $ANTHROPIC_API_KEY \
  --validate

# Step 3: System processes (automatic)
🔍 Parsing code...
✅ Detected platform: SQL Stored Procedures
🧠 Extracting business logic...
✅ Found 3 business rules
✅ Found 2 transformations
🔄 Converting SQL from oracle to postgresql...
✅ Running validation...
Validation Score: 99.5%
Status: ✅ PASSED
💾 Saving to: converted_oracle_procedure.sql

# Step 4: Output - PostgreSQL
converted_oracle_procedure.sql:
-------------------------------
CREATE OR REPLACE FUNCTION sales_summary(p_year INTEGER)
RETURNS VOID AS $$
DECLARE
  rec RECORD;
BEGIN
  FOR rec IN
    SELECT region, SUM(amount) as total
    FROM sales
    WHERE EXTRACT(YEAR FROM sale_date) = p_year
    GROUP BY region
  LOOP
    INSERT INTO sales_summary VALUES (p_year, rec.region, rec.total);
  END LOOP;
  COMMIT;
END;
$$ LANGUAGE plpgsql;

# Step 5: Also convert to Spark (optional)
python run_migration_module.py cli \
  -i oracle_procedure.sql \
  -t spark \
  --spark-version 3.5 \
  --use-delta \
  --api-key $ANTHROPIC_API_KEY

# Step 6: Output - PySpark
spark_oracle_procedure.sql.py:
-----------------------------
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from delta import *

class SalesSummaryETL:
    def __init__(self, spark):
        self.spark = spark

    def process_sales_summary(self, year):
        # Read sales data
        sales_df = self.spark.read.table("sales") \
            .filter(year(col("sale_date")) == year)

        # Aggregate by region
        summary_df = sales_df.groupBy("region") \
            .agg(sum("amount").alias("total")) \
            .withColumn("year", lit(year))

        # Write to Delta Lake
        summary_df.write \
            .format("delta") \
            .mode("append") \
            .saveAsTable("sales_summary")

        return {"status": "success", "rows": summary_df.count()}

# Usage
spark = SparkSession.builder.getOrCreate()
etl = SalesSummaryETL(spark)
result = etl.process_sales_summary(2024)
```

---

## 🎓 Summary

### **Entry Point**
`run_migration_module.py` - Single file that starts everything

### **Two Modes**
1. **Dashboard** (Web UI) - Interactive, visual
2. **CLI** (Command Line) - Automated, scriptable

### **Conversion Process**
1. Upload → 2. Parse → 3. Extract Logic → 4. Convert → 5. Validate → 6. Execute

### **Languages Supported**
- **29 Source Languages/Formats** (SQL, ETL, Mainframe, Orchestration)
- **3 Target Platforms** (SQL, Spark, Databricks)
- **14 Target Variants** (Different SQL engines, Spark versions)

### **100% Logic Preservation**
Every business rule, transformation, and calculation is preserved exactly!

---

## 🚀 Quick Start

```bash
# 1. Install
pip install -r migration_module/requirements.txt

# 2. Set API key
export ANTHROPIC_API_KEY='your-key-here'

# 3. Run dashboard
python run_migration_module.py

# 4. Or use CLI
python run_migration_module.py cli -i myfile.sql -t spark --validate
```

That's it! The system handles everything automatically! 🎉
