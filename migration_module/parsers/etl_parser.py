"""
AI-Powered ETL Parser
Parses Talend, DataStage, Informatica, SSIS, and other ETL tools
"""

import re
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import anthropic
from ..config import AI_CONFIG


class ETLParser:
    """Parse ETL tool definitions using AI"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.ai_config = AI_CONFIG['code_parser']

    def parse(self, etl_code: str, platform: str) -> Dict:
        """
        Parse ETL code based on platform
        """
        parsers = {
            'talend': self._parse_talend,
            'datastage': self._parse_datastage,
            'informatica': self._parse_informatica,
            'ssis': self._parse_ssis,
            'abinitio': self._parse_abinitio,
            'pentaho': self._parse_pentaho
        }

        parser = parsers.get(platform, self._parse_generic)
        traditional_result = parser(etl_code)

        # AI enhancement
        if self.client:
            ai_result = self._ai_parse_etl(etl_code, platform)
            traditional_result['ai_insights'] = ai_result

        return traditional_result

    def _parse_talend(self, code: str) -> Dict:
        """Parse Talend job XML"""
        result = {
            'platform': 'talend',
            'components': [],
            'connections': [],
            'sources': [],
            'targets': [],
            'transformations': [],
            'lookup_tables': [],
            'variables': [],
            'context_params': []
        }

        try:
            root = ET.fromstring(code)

            # Extract components
            for node in root.findall('.//node'):
                component = {
                    'type': node.get('componentName'),
                    'name': node.get('componentVersion'),
                    'properties': {}
                }

                # Extract properties
                for elem_param in node.findall('.//elementParameter'):
                    param_name = elem_param.get('name')
                    param_value = elem_param.get('value')
                    component['properties'][param_name] = param_value

                result['components'].append(component)

                # Classify component
                comp_type = component['type'].lower()
                if 'input' in comp_type or 'extract' in comp_type:
                    result['sources'].append(component)
                elif 'output' in comp_type or 'load' in comp_type:
                    result['targets'].append(component)
                elif 'map' in comp_type or 'filter' in comp_type or 'aggregate' in comp_type:
                    result['transformations'].append(component)
                elif 'lookup' in comp_type:
                    result['lookup_tables'].append(component)

            # Extract connections
            for connection in root.findall('.//connection'):
                result['connections'].append({
                    'from': connection.get('source'),
                    'to': connection.get('target'),
                    'type': connection.get('connectorName')
                })

        except ET.ParseError as e:
            result['parse_error'] = str(e)

        return result

    def _parse_datastage(self, code: str) -> Dict:
        """Parse DataStage DSX export"""
        result = {
            'platform': 'datastage',
            'jobs': [],
            'stages': [],
            'links': [],
            'sources': [],
            'targets': [],
            'transformations': []
        }

        try:
            root = ET.fromstring(code)

            # Extract jobs
            for job in root.findall('.//Job'):
                job_info = {
                    'name': job.get('Identifier'),
                    'stages': [],
                    'links': []
                }

                # Extract stages
                for stage in job.findall('.//Stage'):
                    stage_info = {
                        'name': stage.get('Name'),
                        'type': stage.get('StageType'),
                        'properties': {}
                    }

                    # Get properties
                    for prop in stage.findall('.//Property'):
                        stage_info['properties'][prop.get('Name')] = prop.text

                    job_info['stages'].append(stage_info)
                    result['stages'].append(stage_info)

                    # Classify stage
                    stage_type = stage_info['type'].lower()
                    if 'sequential' in stage_type or 'source' in stage_type:
                        result['sources'].append(stage_info)
                    elif 'target' in stage_type or 'load' in stage_type:
                        result['targets'].append(stage_info)
                    elif 'transformer' in stage_type or 'aggregator' in stage_type:
                        result['transformations'].append(stage_info)

                # Extract links
                for link in job.findall('.//Link'):
                    link_info = {
                        'from': link.get('From'),
                        'to': link.get('To'),
                        'name': link.get('Name')
                    }
                    job_info['links'].append(link_info)
                    result['links'].append(link_info)

                result['jobs'].append(job_info)

        except ET.ParseError as e:
            result['parse_error'] = str(e)

        return result

    def _parse_informatica(self, code: str) -> Dict:
        """Parse Informatica PowerCenter XML"""
        result = {
            'platform': 'informatica',
            'mappings': [],
            'sources': [],
            'targets': [],
            'transformations': [],
            'workflows': [],
            'sessions': []
        }

        try:
            root = ET.fromstring(code)

            # Extract mappings
            for mapping in root.findall('.//MAPPING'):
                mapping_info = {
                    'name': mapping.get('NAME'),
                    'transformations': [],
                    'connectors': []
                }

                # Extract transformations
                for trans in mapping.findall('.//TRANSFORMATION'):
                    trans_info = {
                        'name': trans.get('NAME'),
                        'type': trans.get('TYPE'),
                        'properties': {},
                        'ports': []
                    }

                    # Extract ports
                    for port in trans.findall('.//TRANSFORMFIELD'):
                        trans_info['ports'].append({
                            'name': port.get('NAME'),
                            'datatype': port.get('DATATYPE'),
                            'precision': port.get('PRECISION'),
                            'expression': port.get('EXPRESSION')
                        })

                    mapping_info['transformations'].append(trans_info)
                    result['transformations'].append(trans_info)

                    # Classify transformation
                    trans_type = trans_info['type']
                    if trans_type in ['Source Qualifier', 'Source']:
                        result['sources'].append(trans_info)
                    elif trans_type == 'Target':
                        result['targets'].append(trans_info)

                # Extract connectors
                for connector in mapping.findall('.//CONNECTOR'):
                    mapping_info['connectors'].append({
                        'from': connector.get('FROMINSTANCE'),
                        'to': connector.get('TOINSTANCE')
                    })

                result['mappings'].append(mapping_info)

            # Extract workflows
            for workflow in root.findall('.//WORKFLOW'):
                result['workflows'].append({
                    'name': workflow.get('NAME'),
                    'description': workflow.get('DESCRIPTION')
                })

        except ET.ParseError as e:
            result['parse_error'] = str(e)

        return result

    def _parse_ssis(self, code: str) -> Dict:
        """Parse SSIS package"""
        result = {
            'platform': 'ssis',
            'packages': [],
            'data_flows': [],
            'control_flows': [],
            'sources': [],
            'destinations': [],
            'transformations': []
        }

        try:
            root = ET.fromstring(code)

            # Extract executables (tasks/containers)
            for executable in root.findall('.//{*}Executable'):
                exec_type = executable.get('{http://www.w3.org/2001/XMLSchema-instance}type')

                if 'Pipeline' in str(exec_type):
                    # Data flow task
                    dataflow = {
                        'name': executable.get('Name'),
                        'components': []
                    }

                    # Extract components
                    for component in executable.findall('.//{*}component'):
                        comp_info = {
                            'name': component.get('name'),
                            'type': component.get('componentClassID'),
                            'properties': {}
                        }
                        dataflow['components'].append(comp_info)

                        # Classify
                        comp_id = comp_info['type'] or ''
                        if 'Source' in comp_id:
                            result['sources'].append(comp_info)
                        elif 'Destination' in comp_id:
                            result['destinations'].append(comp_info)
                        else:
                            result['transformations'].append(comp_info)

                    result['data_flows'].append(dataflow)
                else:
                    result['control_flows'].append({
                        'name': executable.get('Name'),
                        'type': exec_type
                    })

        except ET.ParseError as e:
            result['parse_error'] = str(e)

        return result

    def _parse_abinitio(self, code: str) -> Dict:
        """Parse Ab Initio graph"""
        result = {
            'platform': 'abinitio',
            'components': [],
            'sources': [],
            'targets': [],
            'transforms': []
        }

        # Ab Initio uses proprietary format, parse key patterns
        lines = code.split('\n')
        for line in lines:
            if '.component' in line:
                component = {'definition': line.strip()}
                result['components'].append(component)

        return result

    def _parse_pentaho(self, code: str) -> Dict:
        """Parse Pentaho transformation or job"""
        result = {
            'platform': 'pentaho',
            'steps': [],
            'hops': [],
            'sources': [],
            'targets': [],
            'transformations': []
        }

        try:
            root = ET.fromstring(code)

            # Check if transformation or job
            is_transformation = root.tag == 'transformation'

            # Extract steps
            for step in root.findall('.//step'):
                step_info = {
                    'name': step.findtext('name'),
                    'type': step.findtext('type'),
                    'properties': {}
                }

                result['steps'].append(step_info)

                # Classify
                step_type = step_info['type'].lower()
                if 'input' in step_type or 'table' in step_type:
                    result['sources'].append(step_info)
                elif 'output' in step_type:
                    result['targets'].append(step_info)
                else:
                    result['transformations'].append(step_info)

            # Extract hops (connections)
            for hop in root.findall('.//hop'):
                result['hops'].append({
                    'from': hop.findtext('from'),
                    'to': hop.findtext('to'),
                    'enabled': hop.findtext('enabled')
                })

        except ET.ParseError as e:
            result['parse_error'] = str(e)

        return result

    def _parse_generic(self, code: str) -> Dict:
        """Generic parser for unknown formats"""
        return {
            'platform': 'unknown',
            'raw_content': code[:1000],  # First 1000 chars
            'needs_ai_analysis': True
        }

    def _ai_parse_etl(self, code: str, platform: str) -> Dict:
        """Use AI to extract business logic from ETL"""
        prompt = f"""Analyze this {platform} ETL job and extract:

1. **Data Sources**: All input sources with schemas
2. **Data Targets**: All output destinations
3. **Transformations**: Every data transformation step
4. **Business Logic**: Rules, filters, calculations
5. **Data Quality**: Validation rules and checks
6. **Lookup/Join Logic**: Reference data and join conditions
7. **Aggregations**: Grouping and aggregation logic
8. **Error Handling**: How errors are handled
9. **Data Lineage**: Complete data flow from source to target
10. **Performance Considerations**: Partitioning, caching, etc.

ETL Code:
```
{code[:8000]}  # Limit for token size
```

Provide a comprehensive analysis that would allow recreating this ETL in Spark."""

        try:
            response = self.client.messages.create(
                model=self.ai_config['model'],
                max_tokens=self.ai_config['max_tokens'],
                temperature=self.ai_config['temperature'],
                messages=[{"role": "user", "content": prompt}]
            )

            return {
                'analysis': response.content[0].text,
                'model': self.ai_config['model']
            }

        except Exception as e:
            return {'ai_error': str(e)}
