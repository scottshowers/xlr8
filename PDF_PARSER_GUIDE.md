# 📄 Advanced PDF Parser User Guide

**Complete guide to parsing pay registers with custom field mappings**

## Overview

The Advanced PDF Parser allows consultants to extract payroll data from complex PDF pay registers and map fields to UKG-compatible formats. This guide covers both automatic parsing and custom mapping workflows.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Auto-Detection Mode](#auto-detection-mode)
3. [Custom Mapping Mode](#custom-mapping-mode)
4. [Mapping Editor Guide](#mapping-editor-guide)
5. [Troubleshooting](#troubleshooting)
6. [Best Practices](#best-practices)
7. [Examples](#examples)

---

## Quick Start

### Prerequisites
- XLR8 deployed and accessible
- PDF pay register file (text-based, not scanned)
- Web browser

### Basic Workflow
1. Navigate to "Advanced PDF Parser" tab
2. Upload PDF file
3. Click "Parse PDF"
4. Review results
5. Export to Excel

**That's it for simple cases!**

---

## Auto-Detection Mode

For standard pay registers with common field names.

### When to Use
- Pay register has clear, standard column headers
- Fields like "Employee ID", "Gross Pay", "Net Pay" are present
- First-time parsing of a new customer format
- Quick analysis needed

### Steps

#### 1. Upload PDF
```
1. Click "Choose a PDF file" button
2. Select your pay register PDF
3. Wait for upload (progress bar appears)
4. File name appears when complete
```

#### 2. Configure Options
```
Parsing Options:
☑ Auto-detect pay register fields
☑ Extract all tables

These are recommended defaults!
```

#### 3. Parse
```
1. Click "🚀 Parse PDF" button
2. Wait while processing (5-30 seconds depending on size)
3. Success message appears
```

#### 4. Review Results
```
Results Display:
- Total Pages: 12
- Tables Found: 3
- Total Records: 247 employees
- Pay Register: ✅ Yes

Detected Fields:
- employee_id: EMP ID
- employee_name: Employee Name  
- gross_pay: Gross Earnings
- net_pay: Net Pay
... etc
```

#### 5. Export Data
```
Options:
1. "Download as Excel" - Multi-sheet workbook
2. "Download as CSV" - Combined data
```

### Auto-Detection Field Patterns

The system recognizes these patterns:

**Employee ID**:
- "EMP ID", "Employee ID", "EmpID", "ID"
- "Employee Number", "EMP #", "EE ID"

**Employee Name**:
- "Name", "Employee Name", "Emp Name"
- "Full Name", "Employee"

**Gross Pay**:
- "Gross", "Gross Pay", "Gross Earnings"
- "Total Gross"

**Net Pay**:
- "Net", "Net Pay", "Take Home"
- "Net Amount"

**Hours**:
- "Hours", "Hours Worked", "Regular Hours"
- "Total Hours", "Hrs"

**Rate**:
- "Rate", "Pay Rate", "Hourly Rate"
- "HR Rate"

**Deductions**:
- "Deductions", "Total Deductions"
- "Withheld"

**Taxes**:
- "Tax", "Taxes", "Federal"
- "FICA", "Medicare", "Withholding"

**YTD**:
- "YTD", "Year to Date", "YTD Total"

**Department**:
- "Dept", "Department", "Cost Center"
- "Division"

**Position**:
- "Position", "Job", "Title", "Job Title"

**Date**:
- "Date", "Pay Date", "Check Date", "Period"

---

## Custom Mapping Mode

For pay registers with non-standard or customer-specific field names.

### When to Use
- Column headers don't match standard patterns
- Customer uses unique terminology
- Need to map specific fields differently
- Reusing configuration across multiple similar PDFs

### Workflow

#### Step 1: Generate Mapping Template

1. **Upload your PDF**
2. **Click "🗺️ Generate Mapping Template"**
3. **System analyzes the PDF**:
   - Identifies all column headers
   - Suggests mappings based on auto-detection
   - Creates configuration template

#### Step 2: Download Editor

1. **Click "📝 Download Mapping Editor (HTML)"**
2. **Save the HTML file** (e.g., `mapping_editor_payroll.html`)
3. **Also download "📄 Download Config (JSON)"** (backup)

#### Step 3: Edit Mappings Offline

1. **Open HTML file** in any web browser
2. **Review document information**:
   - Filename
   - Number of pages
   - Tables found
   - Whether detected as pay register

3. **Edit field mappings**:
   - Each row shows a column from your PDF
   - Select target field from dropdown
   - Or type custom field name
   - Auto-detected mappings are pre-selected

4. **Save configuration**:
   - Click "💾 Download Configuration (JSON)"
   - Save JSON file (e.g., `mapping_acme_corp.json`)

#### Step 4: Apply Custom Mapping

Back in XLR8:

1. **Check "📝 Use custom field mapping"**
2. **Upload your JSON configuration file**
3. **Verify** it says "Loaded mapping with X field definitions"
4. **Click "🚀 Parse PDF"**

#### Step 5: Review & Export

1. **Check parsed data** uses your custom field names
2. **Verify** data looks correct
3. **Export to Excel** with properly named columns

---

## Mapping Editor Guide

### Understanding the Interface

#### Document Information Box
```
📄 Document Information
- Filename: Current PDF name
- Pages: Total page count
- Tables Found: Number of tables detected
- Pay Register: Detection result
```

#### Instructions Box
```
📋 Instructions
Step-by-step guidance on:
- How to map fields
- How to save configuration
- How to use in XLR8
```

#### Mapping Table
```
| Source Column       | Target Field    | Auto-Detected |
|--------------------|-----------------|---------------|
| EMP ID             | employee_id     | ✓             |
| Full Name          | employee_name   | ✓             |
| Gross              | gross_pay       | ✓             |
| Custom Field 1     | [dropdown]      |               |
```

### Mapping Field Values

#### Using Dropdowns
1. Click on dropdown in "Target Field" column
2. Select from available fields:
   - employee_id
   - employee_name
   - gross_pay
   - net_pay
   - hours
   - rate
   - deductions
   - taxes
   - ytd
   - department
   - position
   - date
   - custom

#### Custom Field Names
1. Select "custom" from dropdown
2. Or type directly in the field
3. Use for non-standard fields like:
   - bonus_amount
   - overtime_hours
   - shift_differential
   - commission
   - etc.

#### Adding Custom Mappings
1. Click "➕ Add Custom Mapping"
2. Enter source column name
3. Select or type target field
4. Repeat as needed

### Saving Configuration

1. **Review all mappings**
2. **Click "💾 Download Configuration (JSON)"**
3. **File downloads** as `mapping_[filename].json`
4. **Save in organized location**:
   ```
   My Documents/
   └── XLR8 Mappings/
       ├── acme_corp_mapping.json
       ├── global_industries_mapping.json
       └── local_business_mapping.json
   ```

---

## Troubleshooting

### PDF Won't Parse

**Symptoms**: Error message, no tables found

**Causes & Solutions**:

1. **Scanned PDF (Image-based)**
   - **Solution**: PDF must be text-based
   - **Check**: Try selecting text in PDF. If you can't, it's scanned.
   - **Fix**: Use OCR software first, or manual entry

2. **Password-Protected PDF**
   - **Solution**: Remove password first
   - **How**: Open in Adobe Reader, save unlocked copy

3. **Corrupted File**
   - **Solution**: Re-download or re-export PDF
   - **Test**: Try opening in PDF reader

4. **Too Large**
   - **Solution**: Split into smaller files
   - **Limit**: Recommended < 25MB

### Tables Not Detected

**Symptoms**: "Tables Found: 0"

**Causes & Solutions**:

1. **Non-Standard Table Format**
   - **Solution**: Data might be formatted as text, not tables
   - **Check**: Look at PDF - are there clear table borders?
   - **Alternative**: May need manual extraction

2. **Complex Layout**
   - **Solution**: Tables with merged cells may not parse well
   - **Try**: Simplify PDF if possible

3. **Multiple Table Types**
   - **Solution**: Ensure "Extract all tables" is checked
   - **Review**: Check each page individually

### Mapping Not Applying

**Symptoms**: Custom field names don't appear in results

**Causes & Solutions**:

1. **Column Names Don't Match**
   - **Problem**: Column names in JSON don't match PDF
   - **Solution**: Column names are case-sensitive!
   - **Check**: Generate new template to verify exact names

2. **Invalid JSON**
   - **Problem**: JSON file has syntax errors
   - **Solution**: Re-download from mapping editor
   - **Validate**: Use JSON validator online

3. **Mapping Not Uploaded**
   - **Problem**: Forgot to check "Use custom mapping"
   - **Solution**: Enable checkbox and upload JSON

### Excel Export Issues

**Symptoms**: Export fails or file is empty

**Causes & Solutions**:

1. **No Data Parsed**
   - **Problem**: Must successfully parse first
   - **Solution**: Complete parsing before exporting

2. **Memory Issues**
   - **Problem**: Very large dataset
   - **Solution**: Process fewer pages at a time

3. **Browser Issues**
   - **Problem**: Download blocked or failed
   - **Solution**: Try different browser
   - **Check**: Browser download settings

---

## Best Practices

### Mapping Management

1. **Organize Configurations**
   ```
   Create folder structure:
   XLR8 Mappings/
   ├── by-customer/
   │   ├── acme_corp.json
   │   └── global_industries.json
   ├── by-format/
   │   ├── adp_format.json
   │   └── paychex_format.json
   └── templates/
       └── standard_payroll.json
   ```

2. **Naming Conventions**
   ```
   Good names:
   - acme_corp_weekly_payroll.json
   - client_a_biweekly_register.json
   - adp_standard_format_v1.json

   Avoid:
   - mapping1.json
   - test.json
   - config.json
   ```

3. **Version Control**
   ```
   Include version in name if format changes:
   - acme_corp_format_v1.json
   - acme_corp_format_v2.json
   ```

4. **Documentation**
   ```
   Keep notes file alongside mappings:
   - mapping_notes.txt
   Document:
   - Which customers use which mappings
   - Date format was created
   - Any special considerations
   - Known issues or workarounds
   ```

### Parsing Workflow

1. **Test First**
   - Start with small sample (1-2 pages)
   - Verify results before processing full file
   - Adjust mappings if needed

2. **Progressive Enhancement**
   - Start with auto-detection
   - Generate template
   - Customize only fields that need it
   - Test incrementally

3. **Quality Checks**
   - Review sample of parsed data
   - Verify field mappings are correct
   - Check data types (numbers vs text)
   - Validate totals if applicable

4. **Reusability**
   - Save successful configurations
   - Share with team
   - Document customer-specific mappings
   - Build library over time

### Data Validation

**Before Exporting**:
1. Check record count matches
2. Verify key fields populated
3. Spot-check a few rows
4. Look for obviously wrong data
5. Validate totals/summaries

**After Exporting**:
1. Open Excel file
2. Check all sheets loaded
3. Verify column headers
4. Review data types
5. Look for blank cells
6. Compare to source PDF

---

## Examples

### Example 1: Simple Pay Register

**Customer**: Acme Corp  
**Format**: Standard ADP format

```
Steps:
1. Upload acme_weekly_payroll.pdf
2. Auto-detect works perfectly
3. Click Parse PDF
4. Export to Excel
5. Done in 2 minutes!
```

**Result**: All fields detected correctly, no custom mapping needed

### Example 2: Custom Field Names

**Customer**: Global Industries  
**Format**: Custom internal system

**PDF Columns**:
- "EMPNO" (not standard)
- "FULLNAME"
- "REG_PAY"
- "OT_PAY"
- "GROSS_AMT"

**Solution**:
```
1. Upload PDF
2. Generate template
3. Download editor
4. Map fields:
   EMPNO → employee_id
   FULLNAME → employee_name
   REG_PAY → regular_pay (custom)
   OT_PAY → overtime_pay (custom)
   GROSS_AMT → gross_pay
5. Save as global_industries.json
6. Upload mapping, parse PDF
7. Perfect results!
```

### Example 3: Multi-Table Complex Register

**Customer**: TechCorp  
**Format**: 50 pages, 3 tables per page

**Tables**:
1. Employee details (page 1-20)
2. Deductions breakdown (page 21-40)
3. Summary totals (page 41-50)

**Approach**:
```
1. Upload full PDF
2. Ensure "Extract all tables" checked
3. Auto-detect
4. Parse (takes ~30 seconds)
5. Excel output has 150+ sheets (3 per page)
6. Review key sheets
7. Export summary sheet shows totals
```

**Tips for Large Files**:
- Be patient during parsing
- Check Railway hasn't timed out
- Consider splitting if > 100 pages

### Example 4: Reusing Configuration

**Scenario**: Same customer, weekly processing

**Workflow**:
```
Week 1:
1. Create and test mapping
2. Save as weekly_payroll_v1.json

Week 2-52:
1. Upload new PDF
2. Check "Use custom mapping"
3. Upload weekly_payroll_v1.json
4. Click Parse
5. Done in 1 minute!
```

**Benefit**: Consistent mapping across all weeks

---

## Advanced Tips

### Handling Edge Cases

**Mixed Data Types**:
```
Problem: Column has both numbers and text
Solution: Parse as text, convert in Excel as needed
```

**Multiple Header Rows**:
```
Problem: PDF has 2-3 header rows
Solution: System uses first row, may need manual adjustment
```

**Merged Cells**:
```
Problem: Header spans multiple columns
Solution: May create multiple columns, manual cleanup needed
```

**Missing Data**:
```
Problem: Some fields blank in PDF
Solution: Parser preserves blanks, handle in Excel or UKG import
```

### Optimization Tips

**For Faster Processing**:
1. Split large PDFs into manageable chunks
2. Process most recent data only
3. Use selective table extraction if possible

**For Better Accuracy**:
1. Clean up PDF headers before processing
2. Ensure consistent formatting
3. Remove extra pages (cover sheets, etc.)
4. Use clear, standard field names when possible

### Integration with UKG

**After Parsing**:
1. Excel file has clean, mapped data
2. Column names match UKG import templates
3. Data types are correct
4. Ready for import tools

**Recommended Process**:
1. Parse PDF in XLR8
2. Download Excel
3. Final review/cleanup if needed
4. Import to UKG using standard process
5. Validate in UKG system

---

## Keyboard Shortcuts

**In XLR8**:
- No specific shortcuts yet (coming in v3.0)

**In Mapping Editor**:
- Tab: Move to next field
- Enter: Select dropdown item
- Ctrl/Cmd + S: Attempt save (may not work in all browsers)

---

## FAQ

**Q: Can I edit JSON directly instead of using HTML editor?**  
A: Yes, but HTML editor is recommended. JSON must be valid syntax.

**Q: How many PDFs can I process at once?**  
A: Currently one at a time. Batch processing planned for future.

**Q: Can I edit mappings in XLR8 directly?**  
A: Not yet. In-app editor coming in v3.0.

**Q: Will mappings work for similar but not identical PDFs?**  
A: Depends on how similar. If column names match exactly, yes. If different, need new mapping.

**Q: Can I share mappings with teammates?**  
A: Yes! Just share the JSON file. Anyone can upload and use it.

**Q: What if PDF has no tables, just text?**  
A: Parser is optimized for tables. Text-only PDFs may not parse well.

**Q: Can I map one source column to multiple targets?**  
A: No, one-to-one mapping only currently.

**Q: How do I know if auto-detection worked?**  
A: Check the "Detected Fields" section in results.

**Q: Can I edit the HTML editor itself?**  
A: Yes, it's just HTML/JavaScript. Advanced users can customize.

**Q: Is there a limit on PDF size?**  
A: Railway may have limits (usually 25-50MB). Recommend < 25MB.

---

## Support & Feedback

### Getting Help:
1. Review this guide thoroughly
2. Check troubleshooting section
3. Test with sample data
4. Contact HCMPACT support

### Providing Feedback:
- Report bugs or issues
- Suggest improvements
- Share successful configurations
- Request new features

---

**Happy Parsing!** 🎉

**Remember**: Start simple, test thoroughly, build your library of configurations over time.

---

**Version**: 2.0  
**Last Updated**: November 2024
