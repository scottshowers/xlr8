"""
Analysis Workbook Question Parser
Extracts all UKG implementation questions from Analysis_Workbook.xlsx
"""

import pandas as pd
import json
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def parse_analysis_workbook(file_path: str) -> Dict[str, Any]:
    """
    Parse Analysis_Workbook.xlsx and extract all questions.
    
    Returns:
        Dictionary with questions structured by category
    """
    
    all_questions = []
    question_id = 1
    
    # Tabs to skip (reference/home tabs)
    skip_tabs = ['Analysis Tool Home']
    
    xl = pd.ExcelFile(file_path)
    
    for sheet_name in xl.sheet_names:
        if sheet_name in skip_tabs:
            continue
            
        logger.info(f"Processing sheet: {sheet_name}")
        
        try:
            # Read sheet - skip first row (it's usually formatting)
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            
            # Find the header row (contains "Question or Discussion Point")
            header_row = None
            for idx, row in df.iterrows():
                if any('Question' in str(cell) for cell in row):
                    header_row = idx
                    break
            
            if header_row is None:
                logger.warning(f"Could not find header row in {sheet_name}")
                continue
            
            # Extract column indices
            header = df.iloc[header_row]
            question_col = None
            reason_col = None
            notes_col = None
            action_col = None
            
            for idx, val in enumerate(header):
                val_str = str(val).lower()
                if 'question' in val_str or 'discussion' in val_str:
                    question_col = idx
                elif 'reason' in val_str:
                    reason_col = idx
                elif 'hcmpact' in val_str or 'notes' in val_str:
                    notes_col = idx
                elif 'action' in val_str:
                    action_col = idx
            
            if question_col is None:
                logger.warning(f"Could not find question column in {sheet_name}")
                continue
            
            # Process rows after header
            current_section = sheet_name
            
            for idx in range(header_row + 1, len(df)):
                row = df.iloc[idx]
                
                # Get question text
                question_text = row[question_col] if question_col is not None else None
                
                if pd.isna(question_text) or str(question_text).strip() == '':
                    continue
                
                question_text = str(question_text).strip()
                
                # Skip section headers (usually short, no question mark, all caps or bold)
                if len(question_text) < 20 or question_text.isupper():
                    # Might be a section header
                    current_section = question_text
                    continue
                
                # Skip if it's clearly not a question
                if question_text in ['NaN', 'nan', 'None']:
                    continue
                
                # Extract other fields
                reason = ''
                if reason_col is not None and not pd.isna(row[reason_col]):
                    reason = str(row[reason_col]).strip()
                
                notes = ''
                if notes_col is not None and not pd.isna(row[notes_col]):
                    notes = str(row[notes_col]).strip()
                
                action = ''
                if action_col is not None and not pd.isna(row[action_col]):
                    action = str(row[action_col]).strip()
                
                # Determine if required (heuristic: questions with "must", "required", etc.)
                required = any(keyword in question_text.lower() for keyword in ['required', 'must', 'confirm'])
                
                # Extract keywords for better RAG queries
                keywords = extract_keywords(question_text)
                
                # Create question object
                question_obj = {
                    'id': f"q{question_id:03d}",
                    'category': sheet_name,
                    'section': current_section,
                    'question': question_text,
                    'reason': reason,
                    'notes': notes,
                    'action': action,
                    'required': required,
                    'keywords': keywords,
                    'status': 'pending',  # pending, analyzed, reviewed
                    'answer': '',
                    'sources': [],
                    'confidence': 0.0
                }
                
                all_questions.append(question_obj)
                question_id += 1
        
        except Exception as e:
            logger.error(f"Error processing sheet {sheet_name}: {e}")
            continue
    
    # Build final structure
    result = {
        'metadata': {
            'total_questions': len(all_questions),
            'categories': list(set(q['category'] for q in all_questions)),
            'version': '1.0',
            'source': 'Analysis_Workbook.xlsx'
        },
        'questions': all_questions
    }
    
    return result


def extract_keywords(text: str) -> List[str]:
    """
    Extract important keywords from question text for better RAG queries.
    """
    # Remove common words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                  'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'been',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                  'can', 'could', 'may', 'might', 'must', 'shall', 'what', 'when', 'where',
                  'who', 'how', 'why', 'this', 'that', 'these', 'those', 'they', 'them'}
    
    # Extract words
    words = re.findall(r'\b[A-Za-z]{3,}\b', text.lower())
    
    # Filter and return unique keywords
    keywords = [w for w in words if w not in stop_words]
    
    # Return top 10 most relevant (unique)
    return list(dict.fromkeys(keywords))[:10]


def save_questions_database(questions_data: Dict[str, Any], output_path: str):
    """
    Save questions database to JSON file.
    """
    with open(output_path, 'w') as f:
        json.dump(questions_data, f, indent=2)
    
    logger.info(f"Questions database saved to {output_path}")


def load_questions_database(file_path: str) -> Dict[str, Any]:
    """
    Load questions database from JSON file.
    """
    with open(file_path, 'r') as f:
        return json.load(f)


# Main execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python question_parser.py <path_to_Analysis_Workbook.xlsx>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = 'questions_database.json'
    
    print(f"Parsing {input_file}...")
    questions_data = parse_analysis_workbook(input_file)
    
    print(f"\nExtracted {questions_data['metadata']['total_questions']} questions")
    print(f"Categories: {', '.join(questions_data['metadata']['categories'])}")
    
    save_questions_database(questions_data, output_file)
    print(f"\nQuestions database saved to {output_file}")
