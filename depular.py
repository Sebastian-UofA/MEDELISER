import pandas as pd

def split_datetime_column(file_path):
    # Load the Excel file
    df = pd.read_excel(file_path)

    # Assume column F is the 6th column (index 5)
    datetime_col = df.columns[5]
    record_dates = pd.to_datetime(df[datetime_col]).dt.date
    record_times = pd.to_datetime(df[datetime_col]).dt.time

    # Insert new columns right after column F (index 5)
    df.insert(6, 'record', record_dates)
    df.insert(7, 'record time 4', record_times)

    # Overwrite the original file with the new columns
    df.to_excel(file_path, index=False)

def main():
    print("Paste the path to your Excel file:")
    split_datetime_column('your_file.xlsx')