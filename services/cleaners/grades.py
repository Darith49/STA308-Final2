import pandas as pd
from .base import BaseCleaner

class GradesCleaner(BaseCleaner):
    HEADER_ALIASES = {
        'student_id': ['studentid', 'id', 'student_number', 'student_no', 'id_no'],
        'course_code': ['code', 'course_id', 'course_no', 'course_number', 'course'],
        'semester': ['term', 'sem', 'academic_period', 'session'],
        'score': ['grade', 'mark', 'marks', 'total_score', 'points', 'final_score'],
    }
    BUSINESS_KEYS = ['student_id', 'course_code', 'semester']
    REQUIRED_COLUMNS = ['student_id', 'course_code', 'score']

    @staticmethod
    def calculate_grade_letter(score):
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    def clean(self, df):
        self.report['rows_in'] = len(df)
        self.report['invalid_scores'] = 0
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

        if 'semester' not in df.columns:
            df['semester'] = '2024-Fall'

        # Step 4: Deduplicate
        df = self.deduplicate(df)

        valid_rows = []
        for idx, row in df.iterrows():
            row_num = idx + 2
            sid = str(row['student_id']).strip() if pd.notna(row['student_id']) else ''
            code = str(row['course_code']).strip() if pd.notna(row['course_code']) else ''
            
            # Validation: student_id & course_code
            if not sid or sid.lower() in ('nan', 'none', 'null', 'n/a'):
                self.record_error(row_num, 'student_id', row['student_id'], "Missing or invalid student_id; row rejected.")
                self.report['rows_rejected'] += 1
                continue

            if not code or code.lower() in ('nan', 'none', 'null', 'n/a'):
                self.record_error(row_num, 'course_code', row['course_code'], "Missing or invalid course_code; row rejected.")
                self.report['rows_rejected'] += 1
                continue

            # Score validation (0-100 numeric required)
            raw_score = row['score']
            is_valid_score = False
            score_num = None
            try:
                score_num = float(raw_score)
                if 0.0 <= score_num <= 100.0:
                    is_valid_score = True
                else:
                    self.record_error(row_num, 'score', raw_score, f"Score {score_num} is outside allowed range (0.0 - 100.0); row rejected.")
                    self.report['invalid_scores'] += 1
                    self.report['rows_rejected'] += 1
            except (ValueError, TypeError):
                self.record_error(row_num, 'score', raw_score, f"Non-numeric score '{raw_score}'; row rejected.")
                self.report['invalid_scores'] += 1
                self.report['rows_rejected'] += 1

            if not is_valid_score:
                continue

            # Semester
            sem_val = str(row['semester']).strip() if pd.notna(row['semester']) else ''
            if not sem_val or sem_val.lower() in ('nan', 'none', 'null', 'n/a'):
                sem_val = '2024-Fall'

            valid_rows.append({
                'student_id': sid,
                'course_code': code.upper(),
                'semester': sem_val,
                'score': round(score_num, 2),
                'grade_letter': self.calculate_grade_letter(score_num),
            })

        clean_df = pd.DataFrame(valid_rows)
        self.report['rows_ok'] = len(clean_df)
        return clean_df, self.errors, self.report
