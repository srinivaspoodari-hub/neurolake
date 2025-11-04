#!/usr/bin/env python3
"""
NeuroLake Migration Module - Main Entry Point

Run this script to start the migration dashboard or use CLI
"""

import sys
import os
import argparse
from pathlib import Path

# Add migration_module to path
sys.path.insert(0, str(Path(__file__).parent))


def run_dashboard():
    """Run the Streamlit dashboard"""
    from migration_module.migration_dashboard import main
    main()


def run_cli(args):
    """Run CLI migration"""
    from migration_module.upload_handler import UploadHandler
    from migration_module.parsers import SQLParser, ETLParser, MainframeParser
    from migration_module.logic_extractor import LogicExtractor
    from migration_module.agents import SQLConverterAgent, SparkConverterAgent
    from migration_module.validators.validation_framework import ValidationFramework

    print("🔄 NeuroLake Migration Module - CLI")
    print("=" * 50)

    # Read input file
    print(f"\n📤 Reading file: {args.input}")
    with open(args.input, 'rb') as f:
        content = f.read()

    # Upload and parse
    handler = UploadHandler()
    print("🔍 Parsing code...")

    metadata = handler.save_upload(
        os.path.basename(args.input),
        content
    )

    platform = metadata['platform']
    print(f"✅ Detected platform: {metadata['platform_name']}")

    # Parse
    decoded_content = content.decode('utf-8')

    if platform == 'sql':
        parser = SQLParser(api_key=args.api_key)
        parsed_data = parser.parse(decoded_content)
    elif platform in ['talend', 'datastage', 'informatica', 'ssis', 'pentaho', 'abinitio']:
        parser = ETLParser(api_key=args.api_key)
        parsed_data = parser.parse(decoded_content, platform)
    elif platform == 'mainframe':
        parser = MainframeParser(api_key=args.api_key)
        parsed_data = parser.parse(decoded_content)
    else:
        print(f"❌ Unsupported platform: {platform}")
        sys.exit(1)

    # Extract logic
    print("\n🧠 Extracting business logic...")
    extractor = LogicExtractor(api_key=args.api_key)
    logic = extractor.extract_logic(decoded_content, platform, parsed_data)
    print(f"✅ Found {len(logic.get('business_rules', []))} business rules")
    print(f"✅ Found {len(logic.get('transformations', []))} transformations")

    # Convert based on target
    if args.target == 'sql':
        print(f"\n🔄 Converting SQL from {args.source_dialect} to {args.target_dialect}...")
        converter = SQLConverterAgent(api_key=args.api_key)
        result = converter.convert(
            original_sql=decoded_content,
            source_dialect=args.source_dialect,
            target_dialect=args.target_dialect,
            extracted_logic=logic,
            optimization_level=args.optimization
        )

        converted_code = result.get('converted_sql', '')
        output_file = args.output or f"converted_{os.path.basename(args.input)}"

    elif args.target == 'spark':
        print(f"\n⚡ Converting to Spark {args.spark_version}...")
        converter = SparkConverterAgent(api_key=args.api_key)
        result = converter.convert_to_spark(
            original_code=decoded_content,
            platform=platform,
            extracted_logic=logic,
            spark_version=args.spark_version,
            use_delta=args.use_delta
        )

        converted_code = result.get('pyspark_code', '')
        output_file = args.output or f"spark_{os.path.basename(args.input)}.py"

    else:
        print(f"❌ Unsupported target: {args.target}")
        sys.exit(1)

    # Validate if requested
    if args.validate:
        print("\n✅ Running validation...")
        validator = ValidationFramework(api_key=args.api_key)
        validation = validator.validate_migration(
            original_code=decoded_content,
            converted_code=converted_code,
            original_platform=platform,
            target_platform=args.target,
            extracted_logic=logic
        )

        print(f"\n{'='*50}")
        print(f"Validation Score: {validation['overall_score']:.1%}")
        print(f"Status: {'✅ PASSED' if validation['passed'] else '❌ FAILED'}")
        print(f"Critical Issues: {len(validation['critical_issues'])}")
        print(f"Warnings: {len(validation['warnings'])}")
        print(f"{'='*50}")

        if not validation['passed']:
            print("\n❌ Validation failed. Review issues before using converted code.")
            if validation['critical_issues']:
                print("\n🚨 Critical Issues:")
                for issue in validation['critical_issues'][:5]:
                    print(f"  - {issue}")

            if not args.force:
                print("\nUse --force to save anyway (not recommended)")
                sys.exit(1)

    # Save output
    print(f"\n💾 Saving to: {output_file}")
    with open(output_file, 'w') as f:
        f.write(converted_code)

    print(f"\n✅ Migration complete!")
    print(f"📄 Output: {output_file}")

    # Generate documentation if requested
    if args.documentation:
        doc_file = f"{output_file}.md"
        print(f"📝 Generating documentation: {doc_file}")
        doc = extractor.generate_documentation(logic)
        with open(doc_file, 'w') as f:
            f.write(doc)
        print(f"✅ Documentation saved: {doc_file}")


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description='NeuroLake Migration Module - AI-Driven Code Migration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run dashboard (recommended)
  python run_migration_module.py

  # CLI: Convert Oracle SQL to PostgreSQL
  python run_migration_module.py cli -i procedure.sql -t sql \\
    --source-dialect oracle --target-dialect postgresql \\
    --api-key YOUR_KEY --validate

  # CLI: Convert Talend job to Spark
  python run_migration_module.py cli -i talend_job.xml -t spark \\
    --api-key YOUR_KEY --spark-version 3.5 --use-delta
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Dashboard command (default)
    dashboard_parser = subparsers.add_parser('dashboard', help='Run interactive dashboard')

    # CLI command
    cli_parser = subparsers.add_parser('cli', help='Run command-line migration')
    cli_parser.add_argument('-i', '--input', required=True, help='Input file path')
    cli_parser.add_argument('-o', '--output', help='Output file path (optional)')
    cli_parser.add_argument('-t', '--target', required=True, choices=['sql', 'spark'],
                           help='Target platform')

    # SQL-specific options
    cli_parser.add_argument('--source-dialect', help='Source SQL dialect (for SQL target)')
    cli_parser.add_argument('--target-dialect', help='Target SQL dialect (for SQL target)')
    cli_parser.add_argument('--optimization', default='balanced',
                           choices=['preserve', 'balanced', 'aggressive'],
                           help='Optimization level')

    # Spark-specific options
    cli_parser.add_argument('--spark-version', default='3.5', help='Spark version')
    cli_parser.add_argument('--use-delta', action='store_true', help='Use Delta Lake')

    # Common options
    cli_parser.add_argument('--api-key', help='Anthropic API key (or set ANTHROPIC_API_KEY env var)')
    cli_parser.add_argument('--validate', action='store_true', help='Run validation')
    cli_parser.add_argument('--force', action='store_true',
                           help='Save output even if validation fails')
    cli_parser.add_argument('--documentation', action='store_true',
                           help='Generate documentation')

    args = parser.parse_args()

    # Get API key from args or environment
    if hasattr(args, 'api_key'):
        args.api_key = args.api_key or os.getenv('ANTHROPIC_API_KEY')

    # Default to dashboard if no command specified
    if not args.command or args.command == 'dashboard':
        print("🚀 Starting NeuroLake Migration Dashboard...")
        print("📱 Open your browser to the URL shown below")
        print()
        run_dashboard()
    elif args.command == 'cli':
        if not args.api_key:
            print("❌ Error: API key required. Set ANTHROPIC_API_KEY or use --api-key")
            sys.exit(1)

        if args.target == 'sql' and (not args.source_dialect or not args.target_dialect):
            print("❌ Error: --source-dialect and --target-dialect required for SQL target")
            sys.exit(1)

        run_cli(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
