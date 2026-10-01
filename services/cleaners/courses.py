import pandas as pd
from .base import BaseCleaner

class CoursesCleaner(BaseCleaner):
    HEADER_ALIASES = {
        'course_code': ['code', 'course_id', 'course_no', 'course_number', 'course'],
        'title': ['course_title', 'course_name', 'name'],
        'credits': ['credit', 'credit_hours', 'units'],
        'department': ['dept', 'dept_code', 'dept_name', 'faculty'],
    }
    BUSINESS_KEYS = ['course_code']
    REQUIRED_COLUMNS = ['course_code']

    def clean(self, df):
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

        for col in ['title', 'credits', 'department']:
            if col not in df.columns:
                df[col] = None

        # Step 4: Deduplicate
        df = self.deduplicate(df)

        valid_rows = []
        for idx, row in df.iterrows():
            row_num = idx + 2
            code_val = str(row['course_code']).strip() if pd.notna(row['course_code']) else ''
            
            if not code_val or code_val.lower() in ('nan', 'none', 'null', 'n/a'):
                self.record_error(row_num, 'course_code', row['course_code'], "Missing or invalid course_code; row rejected.")
                self.report['rows_rejected'] += 1
                continue

            cleaned_row = {'course_code': code_val.upper()}

            # Title
            raw_title = str(row['title']).strip() if pd.notna(row['title']) else ''
            if not raw_title or raw_title.lower() in ('nan', 'none', 'null', 'n/a'):
                cleaned_row['title'] = f"Course {cleaned_row['course_code']}"
                self.report['values_adjusted'] += 1
            else:
                cleaned_row['title'] = raw_title.title()

            # Credits
            raw_credits = row['credits']
            try:
                num_credits = int(float(raw_credits))
                if 1 <= num_credits <= 12:
                    cleaned_row['credits'] = num_credits
                else:
                    self.record_error(row_num, 'credits', raw_credits, f"Credits value {raw_credits} outside reasonable range (1-12); defaulted to 3.")
                    cleaned_row['credits'] = 3
                    self.report['values_adjusted'] += 1
            except (ValueError, TypeError):
                cleaned_row['credits'] = 3
                if pd.notna(raw_credits):
                    self.record_error(row_num, 'credits', raw_credits, f"Non-numeric credits '{raw_credits}'; defaulted to 3.")
                    self.report['values_adjusted'] += 1

            # Department
            raw_dept = str(row['department']).strip() if pd.notna(row['department']) else ''
            if not raw_dept or raw_dept.lower() in ('nan', 'none', 'null', 'n/a'):
                raw_dept = 'General'
            cleaned_row['department'] = raw_dept.upper() if len(raw_dept) <= 6 else raw_dept.title()

            valid_rows.append(cleaned_row)

        clean_df = pd.DataFrame(valid_rows)
        self.report['rows_ok'] = len(clean_df)
        return clean_df, self.errors, self.report
