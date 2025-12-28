"""
XLR8 SECURE 2.0 Analysis Engine
Analyzes customer data for SECURE 2.0 ROTH Catch-up compliance
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class SECURE20Analyzer:
    """
    Analyzes employee data to identify ROTH Catch-up Required (RCR) employees
    and generate compliance action items.
    """
    
    # IRS threshold for SECURE 2.0 (2025)
    WAGE_THRESHOLD = 145000
    AGE_THRESHOLD = 50
    
    # 401k contribution codes (employee only, not loans/match)
    CONTRIB_CODES = ['401P', '401CP', '401F', '401CF']
    ROTH_CODES = ['401R', '401CR', '401RP', '401CRP']  # Common ROTH variants
    
    def __init__(self, excel_file_path: str):
        """
        Initialize analyzer with customer Excel file.
        
        Args:
            excel_file_path: Path to customer data Excel (5 tabs expected)
        """
        self.file_path = excel_file_path
        self.wages_df = None
        self.earnings_df = None
        self.deductions_df = None
        self.emp_deductions_df = None
        self.emp_earnings_df = None
        self.analysis_results = None
        
    def load_data(self) -> bool:
        """Load all sheets from Excel file"""
        try:
            logger.info(f"Loading data from {self.file_path}")
            
            # Load all 5 sheets
            self.wages_df = pd.read_excel(
                self.file_path, 
                sheet_name='Wages Hire Date Pay Freq DOB'
            )
            self.earnings_df = pd.read_excel(
                self.file_path,
                sheet_name='Earnings'
            )
            self.deductions_df = pd.read_excel(
                self.file_path,
                sheet_name='Deductions'
            )
            self.emp_deductions_df = pd.read_excel(
                self.file_path,
                sheet_name='Employee Deductions'
            )
            self.emp_earnings_df = pd.read_excel(
                self.file_path,
                sheet_name='Employee Earnings'
            )
            
            logger.info("Data loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def analyze(self) -> Dict:
        """
        Run complete SECURE 2.0 RCR analysis.
        
        Returns:
            Dictionary with analysis results including:
            - rcr_employees: List of RCR employees
            - high_priority: Employees needing ROTH codes added
            - low_priority: Employees to monitor
            - statistics: Summary stats
        """
        if not self.load_data():
            return {"error": "Failed to load data"}
        
        # Step 1: Extract employee wage data
        employee_wages = self._extract_wage_data()
        
        # Step 2: Calculate ages and RCR status
        employee_wages = self._calculate_rcr_status(employee_wages)
        
        # Step 3: Get 401k participation
        employee_wages = self._add_401k_participation(employee_wages)
        
        # Step 4: Check for existing ROTH codes
        employee_wages = self._check_roth_codes(employee_wages)
        
        # Step 5: Determine action items
        employee_wages = self._determine_actions(employee_wages)
        
        # Step 6: Categorize and summarize
        results = self._categorize_results(employee_wages)
        
        self.analysis_results = results
        return results
    
    def _extract_wage_data(self) -> pd.DataFrame:
        """Extract Medicare wages (proxy for SOC/MED wages)"""
        logger.info("Extracting wage data")
        
        # Filter for USMEDEE (Medicare wages)
        employee_wages = self.wages_df[
            self.wages_df['Tax Code'] == 'USMEDEE'
        ][[
            'Employee Number',
            'Current Taxable Wages 2024',
            'Current Taxable Wages 2025',
            'Date of Birth',
            'Pay Frequency',
            'Hire Date'
        ]].copy()
        
        employee_wages.columns = [
            'Employee Number',
            '2024_SOC_MED_Wages',
            '2025_YTD_SOC_MED_Wages',
            'Date of Birth',
            'Pay Frequency',
            'Hire Date'
        ]
        
        # Ensure Employee Number is string
        employee_wages['Employee Number'] = employee_wages['Employee Number'].astype(str)
        
        return employee_wages
    
    def _calculate_rcr_status(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate if employee is RCR (age 50+ and wages > $145k)"""
        logger.info("Calculating RCR status")
        
        # Age as of 12/31/2025
        target_date = datetime(2025, 12, 31)
        df['Age_12_31_2025'] = df['Date of Birth'].apply(
            lambda x: (target_date - pd.to_datetime(x)).days // 365 if pd.notna(x) else None
        )
        
        # RCR criteria
        df['Age_50_Plus'] = df['Age_12_31_2025'] >= self.AGE_THRESHOLD
        df['Wages_Over_145K'] = df['2024_SOC_MED_Wages'] > self.WAGE_THRESHOLD
        df['Is_RCR_Employee'] = df['Age_50_Plus'] & df['Wages_Over_145K']
        
        logger.info(f"Found {df['Is_RCR_Employee'].sum()} RCR employees")
        
        return df
    
    def _add_401k_participation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add 401k participation info from employee deductions"""
        logger.info("Analyzing 401k participation")
        
        # Ensure Employee Number is string
        self.emp_deductions_df['Employee Number'] = (
            self.emp_deductions_df['Employee Number'].astype(str)
        )
        
        # Filter for 401k codes
        k401_emp = self.emp_deductions_df[
            self.emp_deductions_df['Deduction/Benefit Code'].str.contains('401', na=False)
        ].copy()
        
        # Check if active (no stop date or stop date in future)
        today = pd.Timestamp.now()
        k401_emp['Is_Active'] = (
            k401_emp['Stop Date'].isna() | 
            (pd.to_datetime(k401_emp['Stop Date']) > today)
        )
        
        active_401k = k401_emp[k401_emp['Is_Active']]
        
        # Filter for employee contribution codes only
        active_contrib = active_401k[
            active_401k['Deduction/Benefit Code'].isin(self.CONTRIB_CODES)
        ]
        
        # Summarize by employee
        emp_401k_summary = active_contrib.groupby('Employee Number').agg({
            'Deduction/Benefit Code': lambda x: ', '.join(x.unique()),
            'Amount (Employee)': 'first',
            'Employee Calc Rate Or Percent': 'first'
        }).reset_index()
        
        emp_401k_summary.columns = [
            'Employee Number',
            'Active_401K_Codes',
            'Amount',
            'Percent'
        ]
        
        # Merge with main dataframe
        df = df.merge(emp_401k_summary, on='Employee Number', how='left')
        df['Has_401K'] = df['Active_401K_Codes'].notna()
        
        return df
    
    def _check_roth_codes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Check if employee already has ROTH codes"""
        logger.info("Checking for existing ROTH codes")
        
        # Check employee deductions for ROTH codes
        roth_employees = self.emp_deductions_df[
            self.emp_deductions_df['Deduction/Benefit Code'].str.contains('R401|ROTH', na=False, case=False)
        ]['Employee Number'].unique()
        
        df['Has_ROTH_Code'] = df['Employee Number'].isin(roth_employees)
        
        return df
    
    def _determine_actions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Determine what action is needed for each employee"""
        logger.info("Determining action items")
        
        def get_action(row):
            if not row['Is_RCR_Employee']:
                return 'NO ACTION', 'Not RCR employee'
            
            if not row['Has_401K']:
                return 'MONITOR', 'RCR but no 401k participation'
            
            if row['Has_ROTH_Code']:
                return 'LOW PRIORITY', 'Already has ROTH code - monitor'
            
            return 'HIGH PRIORITY', 'Add ROTH catch-up code'
        
        df[['Action', 'Action_Reason']] = df.apply(
            lambda row: pd.Series(get_action(row)),
            axis=1
        )
        
        return df
    
    def _categorize_results(self, df: pd.DataFrame) -> Dict:
        """Categorize results and generate summary statistics"""
        logger.info("Categorizing results")
        
        # Filter RCR employees only
        rcr_df = df[df['Is_RCR_Employee'] == True].copy()
        rcr_df = rcr_df.sort_values('2024_SOC_MED_Wages', ascending=False)
        
        # Categorize
        high_priority = rcr_df[rcr_df['Action'] == 'HIGH PRIORITY']
        low_priority = rcr_df[rcr_df['Action'] == 'LOW PRIORITY']
        monitor = rcr_df[rcr_df['Action'] == 'MONITOR']
        
        # Statistics
        stats = {
            'total_employees': len(df),
            'rcr_employees': len(rcr_df),
            'high_priority': len(high_priority),
            'low_priority': len(low_priority),
            'monitor': len(monitor),
            'avg_rcr_wages': rcr_df['2024_SOC_MED_Wages'].mean(),
            'highest_wages': rcr_df['2024_SOC_MED_Wages'].max(),
        }
        
        return {
            'all_employees': df,
            'rcr_employees': rcr_df,
            'high_priority': high_priority,
            'low_priority': low_priority,
            'monitor': monitor,
            'statistics': stats
        }
    
    def generate_import_template(self) -> pd.DataFrame:
        """
        Generate bulk import CSV for UKG to add ROTH codes.
        
        Returns:
            DataFrame ready for UKG import tool
        """
        if not self.analysis_results:
            raise ValueError("Run analyze() first")
        
        high_priority = self.analysis_results['high_priority']
        
        # UKG import format
        import_df = pd.DataFrame({
            'Employee Number': high_priority['Employee Number'],
            'Deduction Code': 'R401CU',  # ROTH 401k Catch-up
            'Amount': '',
            'Percent': high_priority['Percent'],
            'Start Date': datetime.now().strftime('%m/%d/%Y')
        })
        
        return import_df


def run_analysis(file_path: str) -> Dict:
    """
    Convenience function to run complete analysis.
    
    Args:
        file_path: Path to customer Excel file
        
    Returns:
        Analysis results dictionary
    """
    analyzer = SECURE20Analyzer(file_path)
    return analyzer.analyze()


if __name__ == "__main__":
    # Test with Meyer data
    results = run_analysis('/mnt/user-data/uploads/Meyer_Secure_2_0.xlsx')
    
    print("\n" + "="*80)
    print("SECURE 2.0 ANALYSIS RESULTS")
    print("="*80)
    
    stats = results['statistics']
    print(f"\nTotal Employees: {stats['total_employees']}")
    print(f"RCR Employees: {stats['rcr_employees']}")
    print(f"  - HIGH Priority (need ROTH codes): {stats['high_priority']}")
    print(f"  - LOW Priority (monitor): {stats['low_priority']}")
    print(f"  - Monitor (no 401k): {stats['monitor']}")
    
    print(f"\nAverage RCR Wages: ${stats['avg_rcr_wages']:,.2f}")
    print(f"Highest Wages: ${stats['highest_wages']:,.2f}")
