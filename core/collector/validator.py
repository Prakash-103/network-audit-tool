import re
from typing import List, Tuple, Optional, Dict

# ── Generic CLI error signatures across standard network CLI engines ──────────
DEFAULT_ERROR_PATTERNS: List[Tuple[str, str]] = [
    # Cisco IOS / IOS-XE / NX-OS
    (r"(?i)%\s*Invalid input detected at", "SYNTAX_ERROR"),
    (r"(?i)%\s*Incomplete command", "INCOMPLETE_COMMAND"),
    (r"(?i)%\s*Ambiguous command", "AMBIGUOUS_COMMAND"),
    (r"(?i)%\s*Bad IP address or host name", "PARAM_ERROR"),
    (r"(?i)%\s*Command rejected", "COMMAND_REJECTED"),
    (r"(?i)%\s*Authorization failed", "AUTH_ERROR"),
    (r"(?i)%\s*Permission denied", "AUTH_ERROR"),
    (r"(?i)%\s*Unknown command", "UNKNOWN_COMMAND"),
    (r"(?i)%\s*Error in authentication", "AUTH_ERROR"),
    (r"(?i)%\s*Login failed", "AUTH_ERROR"),
    # Generic
    (r"(?i)\bCommand not found\b", "UNKNOWN_COMMAND"),
    (r"(?i)\bInvalid syntax\b", "SYNTAX_ERROR"),
    (r"(?i)\bInvalid parameter\b", "PARAM_ERROR"),
    (r"(?i)console>\s*ERROR", "CLI_ERROR"),
    (r"(?i)401\s*Unauthorized", "AUTH_ERROR"),
    (r"(?i)403\s*Forbidden", "AUTH_ERROR"),
    (r"(?i)404\s*Not Found", "NOT_FOUND"),
    (r"(?i)500\s*Internal Server Error", "SERVER_ERROR"),
]

# ── Vendor-specific supplemental error patterns ───────────────────────────────
VENDOR_ERROR_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
    "cisco": [
        (r"(?i)%\s*Unrecognized command", "UNKNOWN_COMMAND"),
        (r"(?i)%\s*Interface does not exist", "NOT_FOUND"),
        (r"(?i)%\s*This command is not supported", "UNSUPPORTED"),
        (r"(?i)%\s*No routing protocol specified", "PARAM_ERROR"),
    ],
    "paloalto": [
        (r"(?i)Unknown command:\s*", "UNKNOWN_COMMAND"),
        (r"(?i)Invalid syntax\.\s*", "SYNTAX_ERROR"),
        (r"(?i)AuthenticationError", "AUTH_ERROR"),
        (r"(?i)Access denied", "AUTH_ERROR"),
        (r"(?i)not found in candidate config", "NOT_FOUND"),
        (r"(?i)request is not supported", "UNSUPPORTED"),
    ],
    "fortinet": [
        (r"(?i)Command fail\.\s*", "COMMAND_FAILED"),
        (r"(?i)entry not found", "NOT_FOUND"),
        (r"(?i)failed to get", "COMMAND_FAILED"),
        (r"(?i)Attribute not recognized", "SYNTAX_ERROR"),
    ],
    "grandstream": [
        (r"(?i)Command not recognized", "UNKNOWN_COMMAND"),
        (r"(?i)Insufficient privilege", "AUTH_ERROR"),
        (r"(?i)Error: Invalid", "SYNTAX_ERROR"),
    ],
    "sophos": [
        (r"(?i)Invalid\s+command", "UNKNOWN_COMMAND"),
        (r"(?i)Error:\s+command not found", "UNKNOWN_COMMAND"),
        (r"(?i)command not supported in this context", "UNSUPPORTED"),
        (r"(?i)Authentication\s+failure", "AUTH_ERROR"),
    ],
    "meraki": [
        (r'(?i)"errors"\s*:\s*\[', "API_ERROR"),
        (r'(?i)"message"\s*:\s*".*not found', "NOT_FOUND"),
        (r'(?i)"message"\s*:\s*".*unauthorized', "AUTH_ERROR"),
        (r'(?i)"message"\s*:\s*".*forbidden', "AUTH_ERROR"),
    ],
    "aruba": [
        (r"(?i)Invalid input", "SYNTAX_ERROR"),
        (r"(?i)Command not supported", "UNSUPPORTED"),
        (r"(?i)Ambiguous entry", "AMBIGUOUS_COMMAND"),
    ],
}

# ── ANSI escape sequence stripper ────────────────────────────────────────────
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class CommandValidator:
    @staticmethod
    def clean_output(output: str) -> str:
        """Strip ANSI escapes, normalize carriage returns and trailing whitespace."""
        if not output:
            return ""
        cleaned = ANSI_ESCAPE_RE.sub('', output)
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        return cleaned.strip()

    @staticmethod
    def get_vendor_patterns(vendor: Optional[str]) -> List[Tuple[str, str]]:
        """Return vendor-specific error patterns for the given vendor string."""
        if not vendor:
            return []
        vendor_lower = vendor.lower()
        patterns: List[Tuple[str, str]] = []
        for key, pat_list in VENDOR_ERROR_PATTERNS.items():
            if key in vendor_lower:
                patterns.extend(pat_list)
        return patterns

    @staticmethod
    def is_valid_output(
        output: str,
        custom_error_patterns: Optional[List[str]] = None,
        vendor: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates whether a command output represents a valid execution or a failure.

        Returns:
            (is_valid: bool, error_classification: Optional[str], matched_snippet: Optional[str])

        Logic:
            - Empty output                  → EMPTY_OUTPUT
            - Custom user-supplied patterns → checked first
            - Vendor-specific patterns      → checked second
            - Generic DEFAULT patterns      → checked last
            - Errors flagged only if matched within FIRST 10 lines (avoids false positives
              from 'description Error backup link' in show run configs)
            - Short outputs (<= 5 lines) are fully scanned
        """
        if not output or not output.strip():
            return False, "EMPTY_OUTPUT", "Received empty response from device"

        cleaned = CommandValidator.clean_output(output)
        all_lines = cleaned.splitlines()
        total_lines = len(all_lines)

        # For short outputs scan all lines; for long outputs only first 10 lines
        # This prevents false positives when show running-config embeds 'Error' in description
        check_lines = all_lines if total_lines <= 10 else all_lines[:10]

        # ── Custom user-supplied error patterns ──────────────────────────────
        if custom_error_patterns:
            for pattern in custom_error_patterns:
                try:
                    for line in check_lines:
                        if re.search(pattern, line):
                            stripped = line.strip()
                            if not stripped.startswith('!') and not re.match(r'(?i)^\s*description\b', stripped):
                                return False, "VENDOR_ERROR_PATTERN", stripped
                except re.error:
                    pass  # ignore malformed patterns

        # ── Vendor-specific patterns ─────────────────────────────────────────
        vendor_patterns = CommandValidator.get_vendor_patterns(vendor)
        for pattern, classification in vendor_patterns:
            for line in check_lines:
                if re.search(pattern, line):
                    stripped = line.strip()
                    if not stripped.startswith('!') and not re.match(r'(?i)^\s*description\b', stripped):
                        return False, classification, stripped

        # ── Generic / Default error patterns ─────────────────────────────────
        for pattern, classification in DEFAULT_ERROR_PATTERNS:
            for line in check_lines:
                if re.search(pattern, line):
                    stripped = line.strip()
                    # Skip comment lines and description keywords
                    if stripped.startswith('!') or re.match(r'(?i)^\s*description\b', stripped):
                        continue
                    return False, classification, stripped

        return True, None, None

    @staticmethod
    def sanitize_filename_cmd(command: str) -> str:
        """
        Converts a show command into a clean filename component.
        E.g. 'show ip interface brief' -> 'sh_ip_interface_brief'
             'cat /etc/version'        -> 'sh_cat_etc_version'
             '/api/v1/devices/{serial}'-> 'sh_api_v1_devices_serial'
        """
        cmd = command.strip().lower()
        if cmd.startswith("show "):
            cmd = "sh_" + cmd[5:]
        elif cmd.startswith("sh "):
            cmd = "sh_" + cmd[3:]
        else:
            cmd = "sh_" + cmd

        # Replace non-alphanumeric characters with underscores
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', cmd)
        # Collapse multiple underscores
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        # Truncate to max 80 chars to keep filenames manageable
        return clean_name[:80]
