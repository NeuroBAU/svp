# Auto-generated stub — do not edit
from typing import Dict, Any, List
HOOKS_JSON_SCHEMA: Dict[str, Any] = {'hooks': {'PreToolUse': [{'type': 'bash', 'matcher': 'write|edit|create', 'script': 'scripts/write_authorization.sh', 'description': 'Universal write authorization'}, {'type': 'bash', 'matcher': 'bash', 'script': 'scripts/non_svp_protection.sh', 'description': 'Non-SVP session protection'}]}}

def check_write_authorization(tool_name: str, file_path: str, pipeline_state_path: str) -> int:
    return 0

def check_svp_session(env_var_name: str) -> int:
    return 0
SVP_ENV_VAR: str = 'SVP_PLUGIN_ACTIVE'
HOOKS_JSON_CONTENT: str
WRITE_AUTHORIZATION_SH_CONTENT: str
NON_SVP_PROTECTION_SH_CONTENT: str
