"""
AI-Powered Mainframe Parser
Parses COBOL, JCL, REXX, and other mainframe code
"""

import re
from typing import Dict, List, Optional
import anthropic
from ..config import AI_CONFIG


class MainframeParser:
    """Parse mainframe code (COBOL, JCL, REXX)"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.ai_config = AI_CONFIG['code_parser']

    def parse(self, code: str) -> Dict:
        """
        Detect and parse mainframe code
        """
        code_type = self._detect_mainframe_type(code)

        parsers = {
            'cobol': self._parse_cobol,
            'jcl': self._parse_jcl,
            'rexx': self._parse_rexx,
            'pl1': self._parse_pl1
        }

        parser = parsers.get(code_type, self._parse_generic)
        result = parser(code)
        result['detected_type'] = code_type

        # AI enhancement
        if self.client:
            result['ai_insights'] = self._ai_parse_mainframe(code, code_type)

        return result

    def _detect_mainframe_type(self, code: str) -> str:
        """Detect mainframe language"""
        if 'IDENTIFICATION DIVISION' in code or 'PROGRAM-ID' in code:
            return 'cobol'
        elif code.strip().startswith('//') and 'JOB' in code:
            return 'jcl'
        elif '/* REXX */' in code or 'parse arg' in code.lower():
            return 'rexx'
        elif '%DCL' in code or 'PROCEDURE OPTIONS' in code:
            return 'pl1'
        return 'unknown'

    def _parse_cobol(self, code: str) -> Dict:
        """Parse COBOL program"""
        result = {
            'type': 'cobol',
            'divisions': {},
            'file_descriptions': [],
            'working_storage': [],
            'procedures': [],
            'paragraphs': [],
            'data_items': [],
            'file_operations': [],
            'database_operations': [],
            'business_logic': []
        }

        # Parse divisions
        divisions = ['IDENTIFICATION', 'ENVIRONMENT', 'DATA', 'PROCEDURE']
        for division in divisions:
            pattern = f'{division}\\s+DIVISION\\.(.+?)(?:(?:{"|".join(divisions)})\\s+DIVISION\\.|$)'
            match = re.search(pattern, code, re.IGNORECASE | re.DOTALL)
            if match:
                result['divisions'][division] = match.group(1).strip()

        # Extract program ID
        prog_id_match = re.search(r'PROGRAM-ID\.\s+(\w+)', code, re.IGNORECASE)
        if prog_id_match:
            result['program_id'] = prog_id_match.group(1)

        # Parse file descriptions (FD)
        fd_pattern = r'FD\s+(\w+).*?(?=FD\s+|WORKING-STORAGE|PROCEDURE|$)'
        for match in re.finditer(fd_pattern, code, re.IGNORECASE | re.DOTALL):
            result['file_descriptions'].append({
                'file_name': match.group(1),
                'definition': match.group(0).strip()
            })

        # Parse working storage
        ws_section = result['divisions'].get('DATA', '')
        if 'WORKING-STORAGE SECTION' in ws_section:
            # Extract 01 level items
            level_01_pattern = r'01\s+(\w+).*?\.'
            for match in re.finditer(level_01_pattern, ws_section, re.IGNORECASE):
                result['working_storage'].append({
                    'name': match.group(1),
                    'definition': match.group(0).strip()
                })

        # Parse procedures
        proc_division = result['divisions'].get('PROCEDURE', '')
        if proc_division:
            # Extract paragraphs
            para_pattern = r'^([A-Z0-9-]+)\s*\.'
            for match in re.finditer(para_pattern, proc_division, re.MULTILINE):
                result['paragraphs'].append(match.group(1))

            # Extract file operations
            file_ops = ['OPEN', 'CLOSE', 'READ', 'WRITE', 'REWRITE', 'DELETE']
            for op in file_ops:
                op_pattern = f'{op}\\s+(\\w+)'
                for match in re.finditer(op_pattern, proc_division, re.IGNORECASE):
                    result['file_operations'].append({
                        'operation': op,
                        'file': match.group(1)
                    })

            # Extract database operations
            db_ops = ['EXEC SQL', 'EXEC CICS']
            for op in db_ops:
                if op in proc_division:
                    result['database_operations'].append({
                        'type': op,
                        'found': True
                    })

        return result

    def _parse_jcl(self, code: str) -> Dict:
        """Parse JCL (Job Control Language)"""
        result = {
            'type': 'jcl',
            'job_name': None,
            'job_card': None,
            'steps': [],
            'datasets': [],
            'programs': [],
            'procedures': []
        }

        lines = code.split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('//*'):
                continue

            # Job card
            if line.startswith('//') and ' JOB ' in line:
                job_match = re.match(r'//(\w+)\s+JOB', line)
                if job_match:
                    result['job_name'] = job_match.group(1)
                    result['job_card'] = line

            # Exec statement (step)
            elif line.startswith('//') and ' EXEC ' in line:
                step_match = re.match(r'//(\w+)\s+EXEC\s+(?:PGM=(\w+)|PROC=(\w+))', line)
                if step_match:
                    step_name = step_match.group(1)
                    program = step_match.group(2)
                    procedure = step_match.group(3)

                    step = {
                        'name': step_name,
                        'line': line
                    }

                    if program:
                        step['program'] = program
                        result['programs'].append(program)
                    elif procedure:
                        step['procedure'] = procedure
                        result['procedures'].append(procedure)

                    result['steps'].append(step)

            # DD statement (dataset)
            elif line.startswith('//') and ' DD ' in line:
                dd_match = re.match(r'//(\w+)\s+DD\s+(.*)', line)
                if dd_match:
                    dd_name = dd_match.group(1)
                    dd_params = dd_match.group(2)

                    # Extract DSN
                    dsn_match = re.search(r'DSN=([^,\s]+)', dd_params)
                    if dsn_match:
                        result['datasets'].append({
                            'dd_name': dd_name,
                            'dsn': dsn_match.group(1),
                            'params': dd_params
                        })

        return result

    def _parse_rexx(self, code: str) -> Dict:
        """Parse REXX script"""
        result = {
            'type': 'rexx',
            'variables': [],
            'functions': [],
            'commands': [],
            'file_operations': []
        }

        lines = code.split('\n')

        for line in lines:
            line = line.strip()

            # Variable assignments
            if '=' in line and not line.startswith('/*'):
                var_match = re.match(r'(\w+)\s*=', line)
                if var_match:
                    result['variables'].append(var_match.group(1))

            # Function calls
            func_match = re.match(r'(\w+)\(', line)
            if func_match:
                result['functions'].append(func_match.group(1))

            # TSO/MVS commands
            if line.upper().startswith(('ADDRESS', 'EXECIO', 'LISTDSI')):
                result['commands'].append(line)

        return result

    def _parse_pl1(self, code: str) -> Dict:
        """Parse PL/I code"""
        result = {
            'type': 'pl1',
            'procedures': [],
            'declarations': [],
            'file_operations': []
        }

        # Extract procedures
        proc_pattern = r'(\w+):\s*PROCEDURE.*?END\s+\1;'
        for match in re.finditer(proc_pattern, code, re.IGNORECASE | re.DOTALL):
            result['procedures'].append({
                'name': match.group(1),
                'body': match.group(0)
            })

        # Extract declarations
        dcl_pattern = r'DECLARE\s+(\w+)'
        for match in re.finditer(dcl_pattern, code, re.IGNORECASE):
            result['declarations'].append(match.group(1))

        return result

    def _parse_generic(self, code: str) -> Dict:
        """Generic mainframe parser"""
        return {
            'type': 'unknown_mainframe',
            'raw_content': code[:1000]
        }

    def _ai_parse_mainframe(self, code: str, code_type: str) -> Dict:
        """Use AI to understand mainframe business logic"""
        prompt = f"""Analyze this {code_type.upper()} mainframe code and extract:

1. **Business Purpose**: What does this program/job do?
2. **Input Files/Datasets**: All inputs with their structure
3. **Output Files/Datasets**: All outputs
4. **Business Logic**: Step-by-step logic and transformations
5. **Data Processing**: How data is read, transformed, and written
6. **Validation Rules**: Any data validation or business rules
7. **Error Handling**: How errors are managed
8. **Dependencies**: External programs, files, or databases
9. **Modern Equivalent**: Suggest modern technology equivalents
10. **Migration Path**: Recommended approach to modernize this code

Mainframe Code:
```
{code[:8000]}
```

Provide detailed analysis suitable for migrating to Python/Spark."""

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
