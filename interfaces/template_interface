"""
Template Generator Interface Contract
All template generators MUST follow this interface

Allows different template generation strategies without breaking workflows.
"""

from typing import Protocol, List, Dict, Any, Optional
from pandas import DataFrame
from enum import Enum


class TemplateFormat(Enum):
    """Supported template output formats"""
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    UKG_IMPORT = "ukg_import"


class TemplateType(Enum):
    """Types of templates that can be generated"""
    EARNINGS = "earnings"
    DEDUCTIONS = "deductions"
    TIMEKEEPING = "timekeeping"
    EMPLOYEE_MASTER = "employee_master"
    PAYROLL_BATCH = "payroll_batch"
    CUSTOM = "custom"


class TemplateGeneratorInterface(Protocol):
    """
    Interface contract for template generators.
    
    Any template generation system must follow this interface to be
    compatible with Analysis and Workflow modules.
    
    Team members can create specialized generators (Excel, API, custom formats)
    as long as they follow this contract.
    """
    
    def generate(self,
                data: DataFrame,
                template_type: TemplateType,
                output_format: TemplateFormat = TemplateFormat.EXCEL,
                options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a template from analyzed data.
        
        Args:
            data: Analyzed/parsed DataFrame
            template_type: Type of template to generate
            output_format: Output format
            options: Additional options for generation
        
        Returns:
            {
                'success': bool,
                'file_data': bytes,           # Generated file data
                'filename': str,              # Suggested filename
                'format': str,                # Output format
                'rows_processed': int,        # Number of data rows
                'validation_errors': List[str], # Any validation issues
                'warnings': List[str],        # Non-critical warnings
                'metadata': {                 # Template metadata
                    'created_date': str,
                    'template_version': str,
                    'row_count': int,
                    'column_count': int
                }
            }
        
        Example:
            result = generator.generate(
                data=employee_df,
                template_type=TemplateType.EARNINGS,
                output_format=TemplateFormat.EXCEL
            )
            if result['success']:
                with open(result['filename'], 'wb') as f:
                    f.write(result['file_data'])
        """
        ...
    
    def generate_batch(self,
                      datasets: List[Dict[str, Any]],
                      template_type: TemplateType,
                      output_format: TemplateFormat = TemplateFormat.EXCEL) -> Dict[str, Any]:
        """
        Generate multiple templates at once.
        
        Args:
            datasets: List of dicts with 'data' and 'name' keys
                     [
                         {'name': 'Q1_Earnings', 'data': df1},
                         {'name': 'Q2_Earnings', 'data': df2}
                     ]
            template_type: Type of template
            output_format: Output format
        
        Returns:
            {
                'success': bool,
                'files': List[Dict[str, Any]],  # List of generated files
                'total_rows': int,
                'errors': List[str]
            }
        
        Example:
            datasets = [
                {'name': 'Dept_A', 'data': dept_a_df},
                {'name': 'Dept_B', 'data': dept_b_df}
            ]
            result = generator.generate_batch(datasets, TemplateType.EARNINGS)
        """
        ...
    
    def validate_data(self,
                     data: DataFrame,
                     template_type: TemplateType) -> Dict[str, Any]:
        """
        Validate data before template generation.
        
        Args:
            data: DataFrame to validate
            template_type: Template type for validation rules
        
        Returns:
            {
                'is_valid': bool,
                'required_fields_present': List[str],
                'missing_fields': List[str],
                'data_quality_issues': List[Dict[str, Any]],
                'row_count': int,
                'suggestions': List[str]
            }
        
        Example:
            validation = generator.validate_data(df, TemplateType.EARNINGS)
            if not validation['is_valid']:
                print(f"Missing: {validation['missing_fields']}")
        """
        ...
    
    def apply_mapping(self,
                     data: DataFrame,
                     field_mapping: Dict[str, str],
                     template_type: TemplateType) -> DataFrame:
        """
        Apply field name mapping to data.
        
        Args:
            data: Original DataFrame
            field_mapping: Dict mapping source → target field names
                         {'EMP_ID': 'EmployeeNumber', 'Gross': 'GrossPay'}
            template_type: Template type (for validation)
        
        Returns:
            DataFrame with mapped/renamed columns
        
        Example:
            mapping = {'EMP ID': 'employee_id', 'Name': 'employee_name'}
            mapped_df = generator.apply_mapping(df, mapping, TemplateType.EARNINGS)
        """
        ...
    
    def get_template_schema(self,
                          template_type: TemplateType) -> Dict[str, Any]:
        """
        Get schema/structure for a template type.
        
        Args:
            template_type: Template type
        
        Returns:
            {
                'template_name': str,
                'required_fields': List[str],
                'optional_fields': List[str],
                'field_types': Dict[str, str],  # field_name → data_type
                'field_descriptions': Dict[str, str],
                'validation_rules': Dict[str, Any],
                'example_data': DataFrame
            }
        
        Example:
            schema = generator.get_template_schema(TemplateType.EARNINGS)
            print(f"Required: {schema['required_fields']}")
        """
        ...
    
    def preview_template(self,
                        data: DataFrame,
                        template_type: TemplateType,
                        num_rows: int = 10) -> Dict[str, Any]:
        """
        Generate preview of template without full processing.
        
        Args:
            data: Input DataFrame
            template_type: Template type
            num_rows: Number of preview rows
        
        Returns:
            {
                'preview_html': str,        # HTML table preview
                'preview_data': DataFrame,  # First N rows
                'total_rows': int,
                'columns': List[str],
                'warnings': List[str]
            }
        
        Example:
            preview = generator.preview_template(df, TemplateType.EARNINGS, 5)
            st.markdown(preview['preview_html'], unsafe_allow_html=True)
        """
        ...
    
    def get_generator_info(self) -> Dict[str, Any]:
        """
        Get generator implementation info.
        
        Returns:
            {
                'name': str,                    # Generator name
                'version': str,                 # Version
                'supported_types': List[str],   # Template types supported
                'supported_formats': List[str], # Output formats supported
                'capabilities': List[str]       # Special capabilities
            }
        
        Example:
            info = generator.get_generator_info()
            print(f"Using {info['name']} v{info['version']}")
        """
        ...


class UKGTemplateInterface(Protocol):
    """
    Specialized interface for UKG-specific templates.
    
    Extends TemplateGeneratorInterface with UKG-specific methods.
    """
    
    def generate_ukg_import(self,
                          data: DataFrame,
                          import_type: str,
                          ukg_version: str = "8.1") -> Dict[str, Any]:
        """
        Generate UKG import file.
        
        Args:
            data: Prepared DataFrame
            import_type: 'earnings', 'deductions', 'employee', etc.
            ukg_version: UKG version for compatibility
        
        Returns:
            Same format as generate() with UKG-specific metadata
        
        Example:
            result = generator.generate_ukg_import(
                data=earnings_df,
                import_type='earnings',
                ukg_version='8.1'
            )
        """
        ...
    
    def validate_ukg_format(self,
                          data: DataFrame,
                          import_type: str) -> Dict[str, Any]:
        """
        Validate data meets UKG import requirements.
        
        Args:
            data: DataFrame to validate
            import_type: UKG import type
        
        Returns:
            {
                'ukg_compliant': bool,
                'version_compatible': List[str],
                'format_issues': List[Dict[str, Any]],
                'recommendations': List[str]
            }
        
        Example:
            validation = generator.validate_ukg_format(df, 'earnings')
        """
        ...


# Example implementation
class ExampleTemplateGenerator:
    """
    Example template generator implementation.
    
    Template for team members.
    """
    
    def __init__(self):
        self.name = "ExampleGenerator"
        self.version = "1.0.0"
    
    def generate(self, data: DataFrame, template_type: TemplateType,
                output_format: TemplateFormat = TemplateFormat.EXCEL,
                options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Example implementation"""
        import io
        
        try:
            # Validate first
            validation = self.validate_data(data, template_type)
            if not validation['is_valid']:
                return {
                    'success': False,
                    'file_data': b'',
                    'filename': '',
                    'format': output_format.value,
                    'rows_processed': 0,
                    'validation_errors': validation['data_quality_issues'],
                    'warnings': [],
                    'metadata': {}
                }
            
            # Generate file based on format
            if output_format == TemplateFormat.EXCEL:
                output = io.BytesIO()
                data.to_excel(output, index=False, engine='openpyxl')
                file_data = output.getvalue()
                filename = f"{template_type.value}_template.xlsx"
            
            elif output_format == TemplateFormat.CSV:
                file_data = data.to_csv(index=False).encode('utf-8')
                filename = f"{template_type.value}_template.csv"
            
            else:
                raise ValueError(f"Unsupported format: {output_format}")
            
            return {
                'success': True,
                'file_data': file_data,
                'filename': filename,
                'format': output_format.value,
                'rows_processed': len(data),
                'validation_errors': [],
                'warnings': [],
                'metadata': {
                    'created_date': '2025-11-16',
                    'template_version': self.version,
                    'row_count': len(data),
                    'column_count': len(data.columns)
                }
            }
        
        except Exception as e:
            return {
                'success': False,
                'file_data': b'',
                'filename': '',
                'format': output_format.value,
                'rows_processed': 0,
                'validation_errors': [str(e)],
                'warnings': [],
                'metadata': {}
            }
    
    def generate_batch(self, datasets: List[Dict[str, Any]],
                      template_type: TemplateType,
                      output_format: TemplateFormat = TemplateFormat.EXCEL) -> Dict[str, Any]:
        """Example batch implementation"""
        files = []
        total_rows = 0
        errors = []
        
        for dataset in datasets:
            result = self.generate(
                dataset['data'],
                template_type,
                output_format
            )
            if result['success']:
                files.append(result)
                total_rows += result['rows_processed']
            else:
                errors.extend(result['validation_errors'])
        
        return {
            'success': len(errors) == 0,
            'files': files,
            'total_rows': total_rows,
            'errors': errors
        }
    
    def validate_data(self, data: DataFrame, template_type: TemplateType) -> Dict[str, Any]:
        """Example validation"""
        schema = self.get_template_schema(template_type)
        required = schema['required_fields']
        missing = [f for f in required if f not in data.columns]
        
        return {
            'is_valid': len(missing) == 0,
            'required_fields_present': [f for f in required if f in data.columns],
            'missing_fields': missing,
            'data_quality_issues': [],
            'row_count': len(data),
            'suggestions': [f"Add column: {f}" for f in missing]
        }
    
    def apply_mapping(self, data: DataFrame, field_mapping: Dict[str, str],
                     template_type: TemplateType) -> DataFrame:
        """Example mapping"""
        return data.rename(columns=field_mapping)
    
    def get_template_schema(self, template_type: TemplateType) -> Dict[str, Any]:
        """Example schema"""
        if template_type == TemplateType.EARNINGS:
            return {
                'template_name': 'UKG Earnings',
                'required_fields': ['employee_id', 'earning_code', 'amount'],
                'optional_fields': ['hours', 'date', 'notes'],
                'field_types': {
                    'employee_id': 'string',
                    'earning_code': 'string',
                    'amount': 'float'
                },
                'field_descriptions': {
                    'employee_id': 'Unique employee identifier',
                    'earning_code': 'UKG earning code',
                    'amount': 'Earning amount'
                },
                'validation_rules': {},
                'example_data': DataFrame()
            }
        return {}
    
    def preview_template(self, data: DataFrame, template_type: TemplateType,
                        num_rows: int = 10) -> Dict[str, Any]:
        """Example preview"""
        preview_df = data.head(num_rows)
        return {
            'preview_html': preview_df.to_html(),
            'preview_data': preview_df,
            'total_rows': len(data),
            'columns': list(data.columns),
            'warnings': []
        }
    
    def get_generator_info(self) -> Dict[str, Any]:
        """Example info"""
        return {
            'name': self.name,
            'version': self.version,
            'supported_types': [t.value for t in TemplateType],
            'supported_formats': [f.value for f in TemplateFormat],
            'capabilities': ['batch', 'validation', 'preview']
        }
