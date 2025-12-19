# api/template_management/liquid_validator.py
import re
import json
from liquid import Environment
from typing import List, Set, Optional, Dict
import logging

logger = logging.getLogger(__name__)

class LiquidTemplateValidator:
    """Comprehensive Liquid template validator with all scenarios"""
    
    # Regex patterns
    INCLUDE_REGEX = re.compile(r"{%\s*(-\s*)?include\s+['\"]([^'\"]+)['\"]")
    BLOCK_START_REGEX = re.compile(r"{%\s*(-\s*)?(if|unless|for|case|capture|tablerow)\b.*?(-\s*)?%}")
    BLOCK_END_REGEX = re.compile(r"{%\s*(-\s*)?(endif|endunless|endfor|endcase|endcapture|endtablerow)\s*(-\s*)?%}")
    ELSIF_ELSE_REGEX = re.compile(r"{%\s*(-\s*)?(elseif|else)\b.*?(-\s*)?%}")
    WHEN_REGEX = re.compile(r"{%\s*(-\s*)?when\b.*?(-\s*)?%}")
    ASSIGN_REGEX = re.compile(r"{%\s*assign\s+(\w+)\s*=\s*(.+?)\s*%}")
    COMMENT_REGEX = re.compile(r"{%\s*comment\s*%}(.*?){%\s*endcomment\s*%}", re.DOTALL)
    FILTER_REGEX = re.compile(r"\|\s*([a-zA-Z_]\w*)(?:\s*:\s*([^|}\"']+|\"[^\"]*\"|'[^']*'))?")
    VARIABLE_REGEX = re.compile(r"{{\s*([\w\.\[\]\'\"]+)(?:\s*\|.*?)?\s*}}")
    OUTPUT_EMPTY_REGEX = re.compile(r"{{\s*}}")
    QUOTE_REGEX = re.compile(r"(['\"])(.*?)(?<!\\)\1")
    OPERATOR_REGEX = re.compile(r"(==|!=|<=|>=|<|>|and|or|contains)")
    DOUBLE_DOT_REGEX = re.compile(r"\w+\.\.\w+")
    BREAK_CONTINUE_REGEX = re.compile(r"{%\s*(break|continue)\s*%}")
    
    # Tag mappings
    OPEN_TAGS = {
        "if": "endif",
        "unless": "endunless",
        "for": "endfor",
        "case": "endcase",
        "capture": "endcapture",
        "tablerow": "endtablerow",
        "comment": "endcomment"
    }
    
    # Standard Liquid filters
    ALLOWED_FILTERS = {
        # String filters
        "strip", "lstrip", "rstrip", "upcase", "downcase", "capitalize", "append", 
        "prepend", "replace", "replace_first", "remove", "remove_first", "truncate", 
        "truncatewords", "strip_html", "strip_newlines", "newline_to_br", "escape", 
        "escape_once", "url_encode", "url_decode", "slice", "split",
        # Array filters
        "join", "first", "last", "concat", "map", "reverse", "sort", "sort_natural",
        "uniq", "where", "size", "compact",
        # Math filters
        "abs", "ceil", "floor", "round", "plus", "minus", "times", "divided_by",
        "modulo", "at_least", "at_most",
        # Date filters
        "date", "format_as_date_time",
        # Default filter
        "default",
        # FHIR Converter custom filters (ADD ALL OF THESE)
        "get_first_segments", 
        "get_segment_lists", 
        "get_related_segment_list",
        "get_property_value",
        "add_to_date_time",
        "to_json_string",
        "batch_render",
        "to_array",
        "generate_uuid"
    }
    
    # FHIR Converter custom tags
    FHIR_CUSTOM_TAGS = {"evaluate", "mergeDiff", "addSegment"}
    
    # Reserved Liquid keywords
    RESERVED_KEYWORDS = {
        "true", "false", "nil", "empty", "blank", "forloop", "tablerowloop"
    }

    # Valid Liquid tag keywords
    VALID_TAG_KEYWORDS = {
        # Standard Liquid tags
        "assign", "capture", "case", "comment", "if", "unless", "elseif", "else",
        "for", "break", "continue", "tablerow", "when", "include", "render",
        "cycle", "increment", "decrement", "echo", "liquid", "raw", "endraw",
        # Closing tags
        "endif", "endunless", "endfor", "endcase", "endcapture", "endtablerow", "endcomment",
        # FHIR custom tags
        "evaluate", "mergeDiff", "addSegment"
    }
        
    # Security dangerous patterns
    DANGEROUS_PATTERNS = [
        r"system\s*\(",
        r"exec\s*\(",
        r"eval\s*\(",
        r"__import__",
        r"open\s*\(",
        r"file\s*\(",
    ]
    
    # Performance limits
    MAX_TEMPLATE_SIZE = 1024 * 1024  # 1MB
    MAX_LINE_COUNT = 10000
    MAX_NESTING_DEPTH = 10
    MAX_LOOP_ITERATIONS_WARNING = 1000
    
    def __init__(self, template_root: Optional[str] = None, 
                allowed_variables: Optional[Set[str]] = None,
                required_variables: Optional[Set[str]] = None,
                fhir_validation: bool = True,
                blob_service=None,  # ADD THIS
                source_type: Optional[str] = None):  # ADD THIS
        self.template_root = template_root
        self.allowed_vars = allowed_variables or set()
        self.required_vars = required_variables or set()
        self.fhir_validation = fhir_validation
        self.blob_service = blob_service  # ADD THIS
        self.source_type = source_type  # ADD THIS
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.include_graph: Dict[str, Set[str]] = {}
    
    def validate(self, template_text: str) -> dict:
        """Run all validations and return results"""
        self.errors = []
        self.warnings = []
        
        # Priority 1: Critical validations
        self._validate_encoding(template_text)
        self._validate_template_size(template_text)
        self._validate_empty_content(template_text)
        self._validate_syntax(template_text)
        self._validate_tags(template_text)
        self._validate_tag_keywords(template_text)
        
        # Priority 2: High priority validations
        self._validate_variables(template_text)
        self._validate_security(template_text)
        
        # Priority 3: Medium priority validations
        self._validate_filters(template_text)
        self._validate_expressions(template_text)
        self._validate_control_flow(template_text)
        self._validate_objects(template_text)
        self._validate_strings(template_text)
        self._validate_comments(template_text)
        self._validate_whitespace_control(template_text)
        self._validate_includes(template_text)
        self._validate_assignments(template_text)
        self._validate_output(template_text)
        self._validate_performance(template_text)
        
        # FHIR-specific validation
        if self.fhir_validation:
            self._validate_fhir_specific(template_text)
            self._validate_fhir_dependencies(template_text)
        
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }
    
    # ========== 1. SYNTAX VALIDATION ==========
    def _validate_syntax(self, text: str):
        """Validate basic syntax"""
        # Unmatched tags
        open_liquid = text.count('{%')
        close_liquid = text.count('%}')
        if open_liquid != close_liquid:
            self.errors.append(
                f"Unmatched Liquid tags: {open_liquid} opening '{{%', {close_liquid} closing '%}}'"
            )
        
        # Unmatched output tags
        open_output = text.count('{{')
        close_output = text.count('}}')
        if open_output != close_output:
            self.errors.append(
                f"Unmatched output tags: {open_output} opening '{{{{', {close_output} closing '}}}}'"
            )
        
        # Skip python-liquid parsing if FHIR custom tags are present
        # These tags will cause parse errors but are valid in FHIR Converter
        has_fhir_tags = any(f'{{% {tag}' in text for tag in self.FHIR_CUSTOM_TAGS)
        
        if not has_fhir_tags:
            # Only try to parse if no FHIR custom tags
            try:
                env = Environment()
                env.from_string(text)
            except Exception as e:
                error_msg = str(e).lower()
                # Ignore errors about unknown tags/filters
                if 'unknown' not in error_msg and 'undefined' not in error_msg and 'unregistered' not in error_msg:
                    self.errors.append(f"Liquid parse error: {str(e)}")
                    
    def _validate_tag_keywords(self, text: str):
        """Validate that all tags start with valid keywords"""
        lines = text.splitlines()
        # Match any {% ... %} tag and capture the first word
        tag_pattern = re.compile(r'{%\s*(-\s*)?(\S+)')
        
        for line_number, line in enumerate(lines, start=1):
            for match in tag_pattern.finditer(line):
                first_token = match.group(2)
                
                # Check if it starts with a quote (invalid)
                if first_token.startswith(("'", '"')):
                    self.errors.append(
                        f"Invalid tag syntax at line {line_number}: "
                        f"Tags cannot start with string literals. "
                        f"Found: '{match.group(0)}...'"
                    )
                    continue
                
                # Check if it's a valid keyword
                if first_token not in self.VALID_TAG_KEYWORDS:
                    self.errors.append(
                        f"Unknown tag keyword '{first_token}' at line {line_number}. "
                        f"Tags must start with valid Liquid keywords "
                        f"(assign, include, if, for, etc.)"
                    )
    # ========== 2. TAG VALIDATION ==========
    def _validate_tags(self, text: str):
        """Validate tag usage and pairing"""
        stack = []
        lines = text.splitlines()
        case_stack = []
        
        for line_number, line in enumerate(lines, start=1):
            # Track nesting depth
            if len(stack) > self.MAX_NESTING_DEPTH:
                self.warnings.append(f"Deep nesting detected at line {line_number} (depth: {len(stack)})")
            
            # Find opening tags
            for match in self.BLOCK_START_REGEX.finditer(line):
                tag = match.group(2)
                if tag in self.OPEN_TAGS:
                    stack.append((tag, line_number))
                    if tag == "case":
                        case_stack.append(line_number)
            
            # Find when tags (must be inside case)
            for match in self.WHEN_REGEX.finditer(line):
                if not case_stack:
                    self.errors.append(f"'when' at line {line_number} used outside of 'case' block")
            
            # Find elsif/else tags
            for match in self.ELSIF_ELSE_REGEX.finditer(line):
                tag = match.group(2)
                if not stack or stack[-1][0] not in ["if", "unless"]:
                    self.errors.append(f"'{tag}' at line {line_number} used without preceding 'if' or 'unless'")
            
            # Find closing tags
            for match in self.BLOCK_END_REGEX.finditer(line):
                end_tag = match.group(2)
                
                if not stack:
                    self.errors.append(f"Unexpected '{{{{% {end_tag} %}}}}' at line {line_number}")
                    continue
                
                start_tag, start_line = stack.pop()
                expected = self.OPEN_TAGS.get(start_tag)
                
                if end_tag != expected:
                    self.errors.append(
                        f"Mismatched block: '{{{{% {start_tag} %}}}}' at line {start_line} "
                        f"closed by '{{{{% {end_tag} %}}}}' at line {line_number}. "
                        f"Expected '{{{{% {expected} %}}}}'"
                    )
                
                if end_tag == "endcase" and case_stack:
                    case_stack.pop()
        
        # Check for unclosed blocks
        for start_tag, line_number in stack:
            self.errors.append(
                f"Unclosed block '{{{{% {start_tag} %}}}}' at line {line_number}, "
                f"missing '{{{{% {self.OPEN_TAGS[start_tag]} %}}}}'"
            )
    
    # ========== 3. VARIABLE VALIDATION ==========
    def _validate_variables(self, text: str):
        """Validate variable references"""
        variables = self.VARIABLE_REGEX.findall(text)
        assigned_vars = set()
        
        # Collect assigned variables
        for match in self.ASSIGN_REGEX.finditer(text):
            assigned_vars.add(match.group(1))
        
        for var in variables:
            # Remove array indices and filters
            clean_var = re.sub(r'\[.*?\]', '', var)
            root = clean_var.split(".")[0] if "." in clean_var else clean_var
            
            # Check invalid naming
            if not re.match(r'^[a-zA-Z_]\w*$', root):
                self.errors.append(f"Invalid variable name: '{root}'")
            
            # Check if variable is defined
            if self.allowed_vars and root not in self.allowed_vars and root not in assigned_vars:
                if root not in self.RESERVED_KEYWORDS:
                    self.warnings.append(f"Undefined variable reference: '{{{{ {var} }}}}'")
        
        # Check required variables
        if self.required_vars:
            missing = self.required_vars - assigned_vars - set(variables)
            if missing:
                self.errors.append(f"Missing required variables: {', '.join(missing)}")
    
    # ========== 4. FILTER VALIDATION ==========
    def _validate_filters(self, text: str):
        """Validate filter usage"""
        lines = text.splitlines()
        
        for line_number, line in enumerate(lines, start=1):
            filters = self.FILTER_REGEX.findall(line)
            
            for filter_name, filter_params in filters:
                # Check if filter is known
                if filter_name not in self.ALLOWED_FILTERS:
                    self.warnings.append(
                        f"Unknown filter '{filter_name}' at line {line_number} "
                        f"(may be a FHIR Converter custom filter)"
                    )
                
                # Check filter parameter syntax
                if filter_params:
                    # Check for unmatched quotes in parameters
                    quotes = re.findall(r'["\']', filter_params)
                    if len(quotes) % 2 != 0:
                        self.errors.append(
                            f"Unmatched quotes in filter parameters at line {line_number}: {filter_params}"
                        )
    
    # ========== 5. EXPRESSION VALIDATION ==========
    def _validate_expressions(self, text: str):
        """Validate expressions in conditionals"""
        lines = text.splitlines()
        
        for line_number, line in enumerate(lines, start=1):
            # Find if/unless statements
            if_match = re.search(r'{%\s*(?:if|unless)\s+(.+?)\s*%}', line)
            if if_match:
                expression = if_match.group(1)
                
                # Check for invalid operators
                invalid_ops = re.findall(r'[=!<>]{3,}', expression)
                if invalid_ops:
                    self.errors.append(f"Invalid operator at line {line_number}: {invalid_ops}")
                
                # Check for assignment in condition (single =)
                if re.search(r'\w+\s*=\s*\w+', expression) and '==' not in expression:
                    self.warnings.append(f"Possible assignment in condition at line {line_number}")
    
    # ========== 6. CONTROL FLOW VALIDATION ==========
    def _validate_control_flow(self, text: str):
        """Validate control flow structures"""
        lines = text.splitlines()
        loop_stack = []
        
        for line_number, line in enumerate(lines, start=1):
            # Track loop depth
            if re.search(r'{%\s*for\b', line):
                loop_stack.append(line_number)
            elif re.search(r'{%\s*endfor\s*%}', line):
                if loop_stack:
                    loop_stack.pop()
            
            # Check break/continue outside loops
            if self.BREAK_CONTINUE_REGEX.search(line):
                if not loop_stack:
                    self.errors.append(f"'break' or 'continue' used outside loop at line {line_number}")
    
    # ========== 7. OBJECT/PROPERTY VALIDATION ==========
    def _validate_objects(self, text: str):
        """Validate object access patterns"""
        # Check for double dots
        double_dots = self.DOUBLE_DOT_REGEX.findall(text)
        if double_dots:
            self.errors.append(f"Invalid object access with double dots: {', '.join(set(double_dots))}")
        
        # Check for empty property access
        empty_access = re.findall(r'\w+\.\s*[|}]', text)
        if empty_access:
            self.errors.append(f"Empty property access detected: {len(empty_access)} instances")
    
    # ========== 8. STRING/QUOTE VALIDATION ==========
    def _validate_strings(self, text: str):
        """Validate string and quote usage"""
        lines = text.splitlines()
        
        for line_number, line in enumerate(lines, start=1):
            # Check for unmatched quotes
            single_quotes = line.count("'") - line.count("\\'")
            double_quotes = line.count('"') - line.count('\\"')
            
            if single_quotes % 2 != 0:
                self.errors.append(f"Unmatched single quotes at line {line_number}")
            if double_quotes % 2 != 0:
                self.errors.append(f"Unmatched double quotes at line {line_number}")
    
    # ========== 9. COMMENT VALIDATION ==========
    def _validate_comments(self, text: str):
        """Validate comment blocks"""
        open_comments = text.count('{% comment %}')
        close_comments = text.count('{% endcomment %}')
        
        if open_comments != close_comments:
            self.errors.append(
                f"Unmatched comment tags: {open_comments} opening, {close_comments} closing"
            )
    
    # ========== 10. WHITESPACE CONTROL VALIDATION ==========
    def _validate_whitespace_control(self, text: str):
        """Validate whitespace control usage"""
        # Check for invalid whitespace control
        invalid_ws = re.findall(r'{%\s*-(?![\s%])|(?<![-\s])-\s*%}', text)
        if invalid_ws:
            self.warnings.append(f"Possibly invalid whitespace control syntax: {len(invalid_ws)} instances")
    
    # ========== 11. INCLUDE VALIDATION ==========
    def _validate_includes(self, text: str):
        """Validate include statements and check if files exist in blob storage"""
        lines = text.splitlines()
        include_pattern = re.compile(r"{%\s*(-\s*)?include\s+['\"]([^'\"]+)['\"]")
        
        for line_num, line in enumerate(lines, start=1):
            matches = include_pattern.finditer(line)
            
            for match in matches:
                include_path = match.group(2)
                
                # Check for empty include path
                if not include_path.strip():
                    self.errors.append(f"Line {line_num}: Empty include path detected")
                    continue
                
                # If blob_service and source_type are provided, check if file exists
                if self.blob_service and self.source_type:
                    # Convert include path to blob path
                    # 'Resource/Organization' -> 'HL7/Resource/_Organization.liquid'
                    blob_path = self._convert_include_to_blob_path(include_path)
                    
                    if not self.blob_service.check_blob_exists(blob_path):
                        self.errors.append(
                            f"Line {line_num}: Include file not found: '{include_path}' "
                            f"(Expected blob path: '{blob_path}')"
                        )
                
                # Track for circular dependency checking
                self.include_graph.setdefault("ROOT", set()).add(include_path)
        
        # Check for circular dependencies
        self._validate_circular_includes()
    
    def _convert_include_to_blob_path(self, include_path: str) -> str:
        """
        Convert include path to actual blob storage path
        
        Examples:
            'Resource/Organization' -> 'HL7/Resource/_Organization.liquid'
            'Extensions/Patient/PatientExtension' -> 'HL7/Extensions/Patient/_PatientExtension.liquid'
            'Reference/Account/Subject' -> 'HL7/Reference/Account/_Subject.liquid'
        
        Args:
            include_path: Path from include statement
            
        Returns:
            Full blob path in storage
        """
        # Split path into parts
        parts = include_path.split('/')
        
        if len(parts) == 0:
            return f"{self.source_type}/_unknown.liquid"
        
        # Get the last part (file name)
        file_name = parts[-1]
        
        # Add underscore prefix if not already present
        if not file_name.startswith('_'):
            file_name = f"_{file_name}"
        
        # Add .liquid extension if not present
        if not file_name.endswith('.liquid'):
            file_name = f"{file_name}.liquid"
        
        # Reconstruct path with source_type prefix
        if len(parts) > 1:
            folder_path = '/'.join(parts[:-1])
            blob_path = f"{self.source_type}/{folder_path}/{file_name}"
        else:
            blob_path = f"{self.source_type}/{file_name}"
        
        return blob_path
        
    def _validate_circular_includes(self):
        """Detect circular include dependencies"""
        visited = set()
        stack = set()
        
        def dfs(node):
            if node in stack:
                self.errors.append(f"Circular include dependency detected: {node}")
                return
            if node in visited:
                return
            
            visited.add(node)
            stack.add(node)
            
            for child in self.include_graph.get(node, []):
                dfs(child)
            
            stack.remove(node)
        
        dfs("ROOT")
    
    # ========== 12. ASSIGNMENT VALIDATION ==========
    def _validate_assignments(self, text: str):
        """Validate variable assignments"""
        lines = text.splitlines()
        
        for line_number, line in enumerate(lines, start=1):
            matches = self.ASSIGN_REGEX.finditer(line)
            
            for match in matches:
                var_name = match.group(1)
                
                # Check reserved keywords
                if var_name in self.RESERVED_KEYWORDS:
                    self.errors.append(f"Cannot assign to reserved keyword '{var_name}' at line {line_number}")
                
                # Check invalid variable names
                if not re.match(r'^[a-zA-Z_]\w*$', var_name):
                    self.errors.append(f"Invalid variable name '{var_name}' at line {line_number}")
    
    # ========== 13. OUTPUT VALIDATION ==========
    def _validate_output(self, text: str):
        """Validate output tags"""
        # Check for empty output tags
        empty_outputs = self.OUTPUT_EMPTY_REGEX.findall(text)
        if empty_outputs:
            self.warnings.append(f"Empty output tags detected: {len(empty_outputs)} instances")
    
    # ========== 14. FHIR-SPECIFIC VALIDATION ==========
    def _validate_fhir_specific(self, text: str):
        """Validate FHIR-specific requirements"""
        # Detect FHIR custom tags
        found_custom_tags = []
        for tag in self.FHIR_CUSTOM_TAGS:
            if f'{{% {tag}' in text:
                found_custom_tags.append(tag)
        
        if found_custom_tags:
            self.warnings.append(
                f"FHIR Converter custom tags detected: {', '.join(found_custom_tags)} "
                f"(standard Liquid validation may not apply)"
            )
        
        # Check for resourceType - look more carefully
        has_resource_type = (
            '"resourceType"' in text or 
            "'resourceType'" in text or
            'resourceType' in text  # Without quotes (for variable output)
        )
        
        if not has_resource_type:
            self.warnings.append("FHIR 'resourceType' field not found in template")

    def _validate_fhir_dependencies(self, text: str):
        """
        Validate FHIR pattern: {% evaluate %} should have {% include %}
        But allow exceptions for ID-only evaluations
        """
        
        # Check if template has evaluate tags
        has_evaluate = bool(re.search(r'{%\s*evaluate\s+', text))
        has_include = bool(re.search(r'{%\s*include\s+', text))
        
        if has_evaluate and not has_include:
            self.errors.append(
                "FHIR validation failed: Templates using '{% evaluate %}' must contain '{% include %}' tags."
            )
            return
        
        # Patterns that indicate ID-only evaluation (not resources to include)
        ID_ONLY_PATTERNS = [
            r'ID/Bundle',
            r'ID/Patient.*type:\s*[\'"]First[\'"]',  # First patient ID is often just for reference
            r'ID/Encounter',  # Encounter IDs often used as references
        ]
        
        lines = text.splitlines()
        evaluate_pattern = re.compile(r'{%\s*evaluate\s+(\w+)\s+using\s+[\'"]([^\'"]+)[\'"]')
        include_pattern = re.compile(r'{%\s*include\s+')
        
        for line_num, line in enumerate(lines, start=1):
            evaluate_match = evaluate_pattern.search(line)
            
            if evaluate_match:
                variable_name = evaluate_match.group(1)
                resource_type = evaluate_match.group(2)
                
                # Skip validation for ID-only patterns
                if any(re.search(pattern, line) for pattern in ID_ONLY_PATTERNS):
                    continue
                
                found_include = False
                
                # Look both AHEAD (next 20 lines) and BEHIND (previous 20 lines)
                search_start = max(0, line_num - 21)  # -21 because line_num is 1-indexed
                search_end = min(len(lines), line_num + 19)  # +19 to check 20 lines ahead
                
                for check_idx in range(search_start, search_end):
                    if check_idx == line_num - 1:  # Skip current line
                        continue
                        
                    check_line = lines[check_idx].strip()
                    
                    # Skip empty lines and comments
                    if not check_line or 'comment' in check_line:
                        continue
                    
                    # Found an include that references this variable
                    if include_pattern.search(check_line) and variable_name in check_line:
                        found_include = True
                        break
                    
                    # Also accept any include statement (not just ones that reference the variable)
                    # since includes often happen in batches
                    if include_pattern.search(check_line):
                        found_include = True
                        break
                
                if not found_include:
                    self.warnings.append(  # Changed from errors to warnings
                        f"Line {line_num}: Evaluated variable '{variable_name}' (resource: '{resource_type}') "
                        f"has no corresponding '{{% include %}}' statement within 20 lines. "
                        f"Verify this resource is included in the Bundle output."
                    )
            
    # ========== 15. SECURITY VALIDATION ==========
    def _validate_security(self, text: str):
        """Validate security concerns"""
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                self.errors.append(f"Potentially dangerous pattern detected: {pattern}")
    
    # ========== 16. PERFORMANCE VALIDATION ==========
    def _validate_performance(self, text: str):
        """Validate performance concerns"""
        lines = text.splitlines()
        
        # Check nesting depth
        max_depth = 0
        current_depth = 0
        
        for line in lines:
            current_depth += len(self.BLOCK_START_REGEX.findall(line))
            max_depth = max(max_depth, current_depth)
            current_depth -= len(self.BLOCK_END_REGEX.findall(line))
        
        if max_depth > self.MAX_NESTING_DEPTH:
            self.warnings.append(f"Deep nesting detected: {max_depth} levels (limit: {self.MAX_NESTING_DEPTH})")
        
        # Check for potential infinite loops
        for_loops = re.findall(r'{%\s*for\s+\w+\s+in\s+(.+?)\s*%}', text)
        for loop_range in for_loops:
            if '..' in loop_range:
                range_match = re.search(r'(\d+)\.\.(\d+)', loop_range)
                if range_match:
                    start, end = int(range_match.group(1)), int(range_match.group(2))
                    if end - start > self.MAX_LOOP_ITERATIONS_WARNING:
                        self.warnings.append(
                            f"Large loop range detected: {start}..{end} "
                            f"({end - start} iterations)"
                        )
    
    # ========== 17. ENCODING VALIDATION ==========
    def _validate_encoding(self, text: str):
        """Validate encoding and special characters"""
        try:
            text.encode('utf-8')
        except UnicodeEncodeError as e:
            self.errors.append(f"UTF-8 encoding error: {str(e)}")
        
        # Check for BOM
        if text.startswith('\ufeff'):
            self.warnings.append("Byte Order Mark (BOM) detected at file start")
    
    # ========== 18. TEMPLATE SIZE VALIDATION ==========
    def _validate_template_size(self, text: str):
        """Validate template size limits"""
        size = len(text.encode('utf-8'))
        line_count = len(text.splitlines())
        
        if size > self.MAX_TEMPLATE_SIZE:
            self.errors.append(
                f"Template size ({size} bytes) exceeds maximum ({self.MAX_TEMPLATE_SIZE} bytes)"
            )
        
        if line_count > self.MAX_LINE_COUNT:
            self.errors.append(
                f"Template line count ({line_count}) exceeds maximum ({self.MAX_LINE_COUNT})"
            )
    
    def _validate_empty_content(self, text: str):
        """Check if content is empty"""
        if not text or not text.strip():
            self.errors.append("Template content cannot be empty")