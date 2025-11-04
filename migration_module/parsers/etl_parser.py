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
            'pentaho': self._parse_pentaho,
            'sap_bods': self._parse_sap_bods,
            'odi': self._parse_odi,
            'sas': self._parse_sas,
            'infosphere': self._parse_infosphere,
            'alteryx': self._parse_alteryx,
            'snaplogic': self._parse_snaplogic,
            'matillion': self._parse_matillion,
            'adf': self._parse_adf,
            'glue': self._parse_glue,
            'nifi': self._parse_nifi,
            'airflow': self._parse_airflow,
            'streamsets': self._parse_streamsets
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

    def _parse_sap_bods(self, code: str) -> Dict:
        """Parse SAP Data Services (BODS)"""
        result = {
            'platform': 'sap_bods',
            'jobs': [],
            'workflows': [],
            'dataflows': [],
            'sources': [],
            'targets': [],
            'transformations': []
        }

        try:
            root = ET.fromstring(code)
            # SAP BODS uses ATL format or XML exports
            # Parse job structures, dataflows, and transformations
            for dataflow in root.findall('.//Dataflow'):
                df_info = {
                    'name': dataflow.get('Name'),
                    'components': []
                }
                result['dataflows'].append(df_info)
        except:
            result['note'] = 'SAP BODS requires AI parsing'

        return result

    def _parse_odi(self, code: str) -> Dict:
        """Parse Oracle Data Integrator (ODI)"""
        result = {
            'platform': 'odi',
            'interfaces': [],
            'packages': [],
            'scenarios': [],
            'sources': [],
            'targets': [],
            'mappings': []
        }

        try:
            root = ET.fromstring(code)
            # ODI exports contain interfaces, packages, and scenarios
            for interface in root.findall('.//Interface'):
                result['interfaces'].append({
                    'name': interface.get('Name'),
                    'source': interface.findtext('.//SourceDataStore'),
                    'target': interface.findtext('.//TargetDataStore')
                })
        except:
            result['note'] = 'ODI requires AI parsing'

        return result

    def _parse_sas(self, code: str) -> Dict:
        """Parse SAS ETL Studio / Data Integration"""
        result = {
            'platform': 'sas',
            'programs': [],
            'data_steps': [],
            'proc_steps': [],
            'sources': [],
            'targets': [],
            'transformations': []
        }

        # Parse SAS code patterns
        lines = code.split('\n')
        in_data_step = False

        for line in lines:
            line_upper = line.strip().upper()

            if line_upper.startswith('DATA '):
                in_data_step = True
                result['data_steps'].append(line.strip())
            elif line_upper.startswith('PROC '):
                result['proc_steps'].append(line.strip())
            elif 'SET ' in line_upper or 'MERGE ' in line_upper:
                result['sources'].append(line.strip())

        return result

    def _parse_infosphere(self, code: str) -> Dict:
        """Parse IBM InfoSphere Information Server"""
        result = {
            'platform': 'infosphere',
            'jobs': [],
            'stages': [],
            'sources': [],
            'targets': []
        }

        # InfoSphere is similar to DataStage
        try:
            root = ET.fromstring(code)
            for job in root.findall('.//Job'):
                result['jobs'].append({
                    'name': job.get('Name'),
                    'description': job.get('Description')
                })
        except:
            result['note'] = 'InfoSphere requires AI parsing'

        return result

    def _parse_alteryx(self, code: str) -> Dict:
        """Parse Alteryx Designer workflow"""
        result = {
            'platform': 'alteryx',
            'tools': [],
            'connections': [],
            'sources': [],
            'targets': [],
            'transformations': []
        }

        try:
            root = ET.fromstring(code)
            # Alteryx workflows contain tools and connections
            for node in root.findall('.//Node'):
                tool_id = node.get('ToolID')
                tool_info = {
                    'id': tool_id,
                    'type': node.findtext('.//ToolType'),
                    'config': {}
                }
                result['tools'].append(tool_info)

                # Classify tools
                if tool_id and any(x in tool_id for x in ['Input', 'Read']):
                    result['sources'].append(tool_info)
                elif tool_id and any(x in tool_id for x in ['Output', 'Write']):
                    result['targets'].append(tool_info)
                else:
                    result['transformations'].append(tool_info)

            # Connections
            for conn in root.findall('.//Connection'):
                result['connections'].append({
                    'from': conn.get('name'),
                    'to': conn.get('name')
                })

        except ET.ParseError:
            result['note'] = 'Alteryx requires AI parsing'

        return result

    def _parse_snaplogic(self, code: str) -> Dict:
        """Parse SnapLogic pipeline"""
        result = {
            'platform': 'snaplogic',
            'snaps': [],
            'sources': [],
            'targets': [],
            'transformations': []
        }

        try:
            pipeline = json.loads(code)
            # SnapLogic pipelines are JSON-based
            for snap in pipeline.get('snaps', []):
                snap_info = {
                    'type': snap.get('class_id'),
                    'label': snap.get('label'),
                    'settings': snap.get('settings', {})
                }
                result['snaps'].append(snap_info)

                # Classify snaps
                snap_type = snap_info['type'].lower()
                if 'read' in snap_type or 'source' in snap_type:
                    result['sources'].append(snap_info)
                elif 'write' in snap_type or 'target' in snap_type:
                    result['targets'].append(snap_info)
                else:
                    result['transformations'].append(snap_info)

        except json.JSONDecodeError:
            result['note'] = 'SnapLogic requires AI parsing'

        return result

    def _parse_matillion(self, code: str) -> Dict:
        """Parse Matillion ETL job"""
        result = {
            'platform': 'matillion',
            'components': [],
            'orchestrations': [],
            'transformations': []
        }

        try:
            job = json.loads(code)
            # Matillion uses JSON format
            for component in job.get('components', []):
                result['components'].append({
                    'type': component.get('type'),
                    'name': component.get('name'),
                    'parameters': component.get('parameters', {})
                })
        except json.JSONDecodeError:
            result['note'] = 'Matillion requires AI parsing'

        return result

    def _parse_adf(self, code: str) -> Dict:
        """Parse Azure Data Factory pipeline"""
        result = {
            'platform': 'adf',
            'pipelines': [],
            'activities': [],
            'datasets': [],
            'linked_services': []
        }

        try:
            adf_obj = json.loads(code)
            # ADF uses JSON ARM templates
            if 'properties' in adf_obj:
                props = adf_obj['properties']

                # Parse activities
                for activity in props.get('activities', []):
                    result['activities'].append({
                        'name': activity.get('name'),
                        'type': activity.get('type'),
                        'inputs': activity.get('inputs', []),
                        'outputs': activity.get('outputs', [])
                    })

        except json.JSONDecodeError:
            result['note'] = 'ADF requires AI parsing'

        return result

    def _parse_glue(self, code: str) -> Dict:
        """Parse AWS Glue ETL script"""
        result = {
            'platform': 'glue',
            'script_type': 'python' if 'import' in code else 'scala',
            'sources': [],
            'targets': [],
            'transformations': []
        }

        # Parse Glue PySpark/Scala script
        lines = code.split('\n')
        for line in lines:
            if 'create_dynamic_frame' in line or 'from_catalog' in line:
                result['sources'].append(line.strip())
            elif 'write_dynamic_frame' in line or 'to_catalog' in line:
                result['targets'].append(line.strip())
            elif 'apply_mapping' in line or 'filter' in line:
                result['transformations'].append(line.strip())

        return result

    def _parse_nifi(self, code: str) -> Dict:
        """Parse Apache NiFi flow"""
        result = {
            'platform': 'nifi',
            'processors': [],
            'connections': [],
            'process_groups': []
        }

        try:
            root = ET.fromstring(code)
            # NiFi flows are XML-based
            for processor in root.findall('.//processor'):
                result['processors'].append({
                    'id': processor.get('id'),
                    'type': processor.findtext('type'),
                    'name': processor.findtext('name')
                })

            for connection in root.findall('.//connection'):
                result['connections'].append({
                    'source': connection.findtext('sourceId'),
                    'destination': connection.findtext('destinationId')
                })

        except ET.ParseError:
            result['note'] = 'NiFi requires AI parsing'

        return result

    def _parse_airflow(self, code: str) -> Dict:
        """Parse Apache Airflow DAG"""
        result = {
            'platform': 'airflow',
            'dag_id': None,
            'tasks': [],
            'dependencies': []
        }

        # Parse Python DAG code
        lines = code.split('\n')
        for line in lines:
            if 'dag_id=' in line or 'dag_id =' in line:
                # Extract DAG ID
                match = re.search(r'dag_id\s*=\s*["\']([^"\']+)["\']', line)
                if match:
                    result['dag_id'] = match.group(1)

            # Find task definitions
            if 'task_id=' in line or 'task_id =' in line:
                match = re.search(r'task_id\s*=\s*["\']([^"\']+)["\']', line)
                if match:
                    result['tasks'].append(match.group(1))

            # Find dependencies (>>)
            if '>>' in line:
                result['dependencies'].append(line.strip())

        return result

    def _parse_streamsets(self, code: str) -> Dict:
        """Parse StreamSets Data Collector pipeline"""
        result = {
            'platform': 'streamsets',
            'stages': [],
            'sources': [],
            'processors': [],
            'destinations': []
        }

        try:
            pipeline = json.loads(code)
            # StreamSets pipelines are JSON
            for stage in pipeline.get('stages', []):
                stage_info = {
                    'instance_name': stage.get('instanceName'),
                    'stage_name': stage.get('stageName'),
                    'library': stage.get('library')
                }
                result['stages'].append(stage_info)

                # Classify stages
                library = stage_info['library'].lower()
                if 'origin' in library or 'source' in library:
                    result['sources'].append(stage_info)
                elif 'destination' in library or 'target' in library:
                    result['destinations'].append(stage_info)
                else:
                    result['processors'].append(stage_info)

        except json.JSONDecodeError:
            result['note'] = 'StreamSets requires AI parsing'

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
