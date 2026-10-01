import re
from datetime import datetime, date
import pandas as pd
import numpy as np
from .base import BaseCleaner

class StudentsCleaner(BaseCleaner):
    HEADER_ALIASES = {
        'student_id': ['studentid', 'id', 'student_number', 'id_no', 'student_no', 'id_number'],
        'name': ['full_name', 'student_name', 'fullname', 'names'],
        'gender': ['sex'],
        'department': ['dept', 'dept_name', 'faculty', 'department_code'],
        'program': ['programme', 'degree', 'major', 'course_of_study'],
        'year': ['study_year', 'academic_year', 'level', 'year_of_study'],
        'enrollment_date': ['enrol_date', 'date_enrolled', 'admission_date', 'start_date', 'enrolled_on'],
        'email': ['email_address', 'mail', 'e_mail'],
    }
    BUSINESS_KEYS = ['student_id']
    REQUIRED_COLUMNS = ['student_id']

    GENDER_MAP = {
        'm': 'Male', 'male': 'Male', 'man': 'Male', 'boy': 'Male',
        'f': 'Female', 'female': 'Female', 'woman': 'Female', 'girl': 'Female',
        'other': 'Other', 'non-binary': 'Other', 'unknown': 'Unknown',
    }

    EMAIL_REGEX = re.compile(r'^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$')

    def clean(self, df):
        """
        Cleans students dataset.
        Returns: (clean_df, errors, report)
        """
        self.report['rows_in'] = len(df)
        df = df.copy()

        # Step 1: Normalize headers
        df = self.normalize_headers(df)

        # Step 2: Drop empty rows and trim strings
        df = self.drop_empty_rows_and_cols(df)
        df = self.strip_whitespace(df)

        # Step 3: Check required columns
        for req in self.REQUIRED_COLUMNS:
            if req not in df.columns:
                self.record_error(0, req, None, f"Required column '{req}' is missing from spreadsheet headers.")
                self.report['rows_rejected'] = self.report['rows_in']
                return pd.DataFrame(), self.errors, self.report

        # Ensure all standard columns exist
        for col in ['name', 'gender', 'department', 'program', 'year', 'enrollment_date', 'email']:
            if col not in df.columns:
                df[col] = None

        # Step 4: Deduplicate by student_id
        df = self.deduplicate(df)

        valid_rows = []
        today = date.today()

        for idx, row in df.iterrows():
            row_num = idx + 2  # Excel 1-indexed row including header
            sid = str(row['student_id']).strip() if pd.notna(row['student_id']) else ''
            
            # Reject if student_id is missing or 'nan' / 'null'
            if not sid or sid.lower() in ('nan', 'none', 'null', 'n/a'):
                self.record_error(row_num, 'student_id', row['student_id'], "Missing or invalid student_id; row rejected.")
                self.report['rows_rejected'] += 1
                continue

            cleaned_row = {'student_id': sid}

            # Name
            name_val = str(row['name']).strip() if pd.notna(row['name']) else ''
            if not name_val or name_val.lower() in ('nan', 'none', 'null', 'n/a'):
                cleaned_row['name'] = f"Student {sid}"
                self.report['values_adjusted'] += 1
            else:
                cleaned_row['name'] = name_val.title()

            # Gender
            raw_gender = str(row['gender']).strip().lower() if pd.notna(row['gender']) else ''
            if raw_gender in self.GENDER_MAP:
                std_gender = self.GENDER_MAP[raw_gender]
                if raw_gender != std_gender.lower():
                    self.report['categories_standardized'] += 1
                cleaned_row['gender'] = std_gender
            else:
                cleaned_row['gender'] = 'Unknown'
                if raw_gender and raw_gender not in ('nan', 'null', 'none', ''):
                    self.report['categories_standardized'] += 1

            # Department & Program
            dept_val = str(row['department']).strip() if pd.notna(row['department']) else ''
            if not dept_val or dept_val.lower() in ('nan', 'none', 'null', 'n/a'):
                dept_val = 'General'
            cleaned_row['department'] = dept_val.upper() if len(dept_val) <= 6 else dept_val.title()

            prog_val = str(row['program']).strip() if pd.notna(row['program']) else ''
            if not prog_val or prog_val.lower() in ('nan', 'none', 'null', 'n/a'):
                prog_val = f"Bachelor of {cleaned_row['department']}"
            cleaned_row['program'] = prog_val.title()

            # Year (1-6)
            year_val = row['year']
            cleaned_year = None
            if pd.notna(year_val):
                try:
                    num_yr = int(float(year_val))
                    if 1 <= num_yr <= 6:
                        cleaned_year = num_yr
                    else:
                        self.record_error(row_num, 'year', year_val, f"Year value {year_val} outside allowable range (1-6); set to null.")
                        self.report['values_adjusted'] += 1
                except (ValueError, TypeError):
                    self.record_error(row_num, 'year', year_val, f"Non-numeric year '{year_val}'; set to null.")
                    self.report['values_adjusted'] += 1
            cleaned_row['year'] = cleaned_year

            # Email
            email_val = str(row['email']).strip().lower() if pd.notna(row['email']) else ''
            if email_val and email_val not in ('nan', 'none', 'null', 'n/a'):
                if self.EMAIL_REGEX.match(email_val):
                    cleaned_row['email'] = email_val
                else:
                    self.record_error(row_num, 'email', row['email'], f"Malformed email address '{email_val}'; set to null.")
                    self.report['values_adjusted'] += 1
                    cleaned_row['email'] = None
            else:
                cleaned_row['email'] = None

            # Enrollment Date
            raw_date = row['enrollment_date']
            parsed_date = None
            rejected_date = False
            if pd.notna(raw_date):
                try:
                    if isinstance(raw_date, (datetime, date)):
                        parsed_dt = pd.to_datetime(raw_date)
                    else:
                        try:
                            parsed_dt = pd.to_datetime(str(raw_date).strip(), format='ISO8601')
                        except Exception:
                            parsed_dt = pd.to_datetime(str(raw_date).strip(), dayfirst=True)
                    
                    p_date = parsed_dt.date()
                    if p_date > today:
                        self.record_error(row_num, 'enrollment_date', raw_date, f"Enrollment date {p_date} cannot be in the future; row rejected.")
                        self.report['rows_rejected'] += 1
                        rejected_date = True
                    else:
                        parsed_date = p_date
                except Exception:
                    self.record_error(row_num, 'enrollment_date', raw_date, f"Invalid date format '{raw_date}'; set to null.")
                    self.report['values_adjusted'] += 1
            
            if rejected_date:
                continue

            cleaned_row['enrollment_date'] = parsed_date
            valid_rows.append(cleaned_row)

        clean_df = pd.DataFrame(valid_rows)
        self.report['rows_ok'] = len(clean_df)
        return clean_df, self.errors, self.report
