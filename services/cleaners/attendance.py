from datetime import datetime, date
import pandas as pd
from .base import BaseCleaner

class AttendanceCleaner(BaseCleaner):
    HEADER_ALIASES = {
        'student_id': ['studentid', 'id', 'student_number', 'student_no', 'id_no'],
        'course_code': ['code', 'course_id', 'course_no', 'course_number', 'course'],
        'date': ['attendance_date', 'session_date', 'day', 'class_date'],
        'status': ['attendance', 'state', 'presence', 'mark'],
    }
    BUSINESS_KEYS = ['student_id', 'course_code', 'date']
    REQUIRED_COLUMNS = ['student_id', 'course_code', 'date', 'status']

    STATUS_MAP = {
        'p': 'P', 'present': 'P', '1': 'P', '1.0': 'P', 'yes': 'P',
        'a': 'A', 'absent': 'A', '0': 'A', '0.0': 'A', 'no': 'A',
        'l': 'L', 'late': 'L', 'tardy': 'L',
    }

    def clean(self, df):
        self.report['rows_in'] = len(df)
        self.report['dates_fixed'] = 0
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

        # Step 4: Deduplicate
        df = self.deduplicate(df)

        today = date.today()
        valid_rows = []

        for idx, row in df.iterrows():
            row_num = idx + 2
            sid = str(row['student_id']).strip() if pd.notna(row['student_id']) else ''
            code = str(row['course_code']).strip() if pd.notna(row['course_code']) else ''
            
            if not sid or sid.lower() in ('nan', 'none', 'null', 'n/a'):
                self.record_error(row_num, 'student_id', row['student_id'], "Missing or invalid student_id; row rejected.")
                self.report['rows_rejected'] += 1
                continue

            if not code or code.lower() in ('nan', 'none', 'null', 'n/a'):
                self.record_error(row_num, 'course_code', row['course_code'], "Missing or invalid course_code; row rejected.")
                self.report['rows_rejected'] += 1
                continue

            # Date
            raw_date = row['date']
            parsed_date = None
            if pd.isna(raw_date):
                self.record_error(row_num, 'date', raw_date, "Missing attendance date; row rejected.")
                self.report['rows_rejected'] += 1
                continue

            try:
                if isinstance(raw_date, (datetime, date)):
                    dt = pd.to_datetime(raw_date)
                else:
                    dt = pd.to_datetime(str(raw_date).strip(), dayfirst=True)
                p_date = dt.date()
                if p_date > today:
                    self.record_error(row_num, 'date', raw_date, f"Attendance date {p_date} is in the future; row rejected.")
                    self.report['rows_rejected'] += 1
                    continue
                parsed_date = p_date
                self.report['dates_fixed'] += 1
            except Exception:
                self.record_error(row_num, 'date', raw_date, f"Unparseable date '{raw_date}'; row rejected.")
                self.report['rows_rejected'] += 1
                continue

            # Status standardization
            raw_status = str(row['status']).strip().lower() if pd.notna(row['status']) else ''
            if raw_status in self.STATUS_MAP:
                std_status = self.STATUS_MAP[raw_status]
                if raw_status != std_status.lower():
                    self.report['categories_standardized'] += 1
            else:
                self.record_error(row_num, 'status', row['status'], f"Unknown attendance status '{raw_status}'. Allowed values: Present (P/1), Absent (A/0), Late (L); row rejected.")
                self.report['rows_rejected'] += 1
                continue

            valid_rows.append({
                'student_id': sid,
                'course_code': code.upper(),
                'date': parsed_date,
                'status': std_status,
            })

        clean_df = pd.DataFrame(valid_rows)
        self.report['rows_ok'] = len(clean_df)
        return clean_df, self.errors, self.report
