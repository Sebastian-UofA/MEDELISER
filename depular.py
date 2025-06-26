import pandas as pd
import os
from datetime import datetime, timedelta

def split_datetime_column(df, datetime_col_index=None):
    """
    Split a datetime column into separate date and time columns
    datetime_col_index: index of the column to split (if None, will look for datetime-like columns)
    """
    if datetime_col_index is None:
        # Find the first column that contains datetime-like data
        for i, col in enumerate(df.columns):
            if pd.api.types.is_datetime64_any_dtype(df[col]) or 'time' in col.lower() or 'date' in col.lower():
                datetime_col_index = i
                break
    
    if datetime_col_index is not None:
        datetime_col = df.columns[datetime_col_index]
        
        # Convert to datetime if not already
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        
        # Extract time BEFORE modifying the datetime column
        time_data = df[datetime_col].dt.time
        
        # Create date column (replace the original datetime column)
        df[datetime_col] = df[datetime_col].dt.date
        
        # Insert time column right after the date column
        time_col_name = f"{datetime_col}_time"
        df.insert(datetime_col_index + 1, time_col_name, time_data)
        
        print(f"Split datetime column '{datetime_col}' into date and '{time_col_name}' columns")
    
    return df

def limit_readings_per_day(df, max_readings=7):
    """
    Limit readings to max_readings per meter per day.
    Remove readings that are closest together first.
    """
    # Find date, time, and meter ID columns
    date_col = None
    time_col = None
    meter_col = None
    
    for col in df.columns:
        # Look for date column (Record Time contains the date after splitting)
        if 'record time' in col.lower() and 'time_time' not in col.lower():
            date_col = col
        # Look for time column (Record Time_time contains the time)
        elif 'record time_time' in col.lower() or 'time_time' in col.lower():
            time_col = col
        # Look for meter ID column
        elif 'meter id' in col.lower() or 'meter_id' in col.lower():
            meter_col = col
    
    print(f"Found columns - Date: {date_col}, Time: {time_col}, Meter: {meter_col}")
    
    if not all([date_col, time_col, meter_col]):
        print("Could not find required columns (date, time, meter ID)")
        print("Available columns:", list(df.columns))
        return df
    
    # Fix the warning by making a copy first
    df = df.copy()
    
    # Create datetime column for sorting and comparison
    df['temp_datetime'] = pd.to_datetime(df[date_col].astype(str) + ' ' + df[time_col].astype(str))
    
    # Sort by meter ID, date, then time
    df = df.sort_values([meter_col, date_col, time_col])
    
    filtered_rows = []
    
    # Group by meter and date
    for (meter_id, date), group in df.groupby([meter_col, date_col]):
        if len(group) <= max_readings:
            # If 7 or fewer readings, keep all
            filtered_rows.append(group)
        else:
            # If more than 7 readings, remove closest ones first
            group_copy = group.copy().reset_index(drop=True)
            
            while len(group_copy) > max_readings:
                # Calculate time differences between consecutive readings
                time_diffs = []
                for i in range(len(group_copy) - 1):
                    time_diff = (group_copy.iloc[i+1]['temp_datetime'] - group_copy.iloc[i]['temp_datetime']).total_seconds() / 3600  # in hours
                    time_diffs.append((time_diff, i))
                
                # Find the smallest time difference (closest readings)
                min_diff, min_index = min(time_diffs)
                
                # Remove one of the two closest readings (remove the later one)
                group_copy = group_copy.drop(group_copy.index[min_index + 1]).reset_index(drop=True)
            
            filtered_rows.append(group_copy)
            print(f"Meter {meter_id} on {date}: Reduced from {len(group)} to {len(group_copy)} readings")
    
    # Combine all filtered rows
    result_df = pd.concat(filtered_rows, ignore_index=True)
    
    # Drop temporary datetime column
    result_df = result_df.drop('temp_datetime', axis=1)
    
    return result_df

def split_by_gateway(df):
    """
    Split DataFrame into two based on Gateway column
    Returns tuple: (df_with_gateway, df_without_gateway)
    """
    # Find Gateway column (case-insensitive)
    gateway_col = None
    for col in df.columns:
        if 'gateway' in col.lower():
            gateway_col = col
            break
    
    if gateway_col is None:
        print("No Gateway column found!")
        return df, pd.DataFrame()
    
    # Split data based on Gateway column
    df_with_gateway = df[df[gateway_col].notna() & (df[gateway_col] != '')]
    df_without_gateway = df[df[gateway_col].isna() | (df[gateway_col] == '')]
    
    print(f"Found {len(df_with_gateway)} rows with Gateway")
    print(f"Found {len(df_without_gateway)} rows without Gateway")
    
    return df_with_gateway, df_without_gateway

def append_all_sheets(file_path):
    # Convert .xls to .xlsx if needed
    if file_path.endswith('.xls'):
        # Read with xlrd engine for .xls files
        all_sheets = pd.read_excel(file_path, sheet_name=None, engine='xlrd')
        # Create new .xlsx file path
        xlsx_path = file_path.replace('.xls', '.xlsx')
    else:
        all_sheets = pd.read_excel(file_path, sheet_name=None)
        xlsx_path = file_path
    
    dataframes = []
    
    for i, (sheet_name, df) in enumerate(all_sheets.items()):
        if i == 0:
            # Keep all data from the first sheet (including headers)
            dataframes.append(df)
        else:
            # For subsequent sheets, keep all data rows (pandas already handles headers automatically)
            dataframes.append(df)
    
    # Concatenate all DataFrames
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    # Split datetime column
    combined_df = split_datetime_column(combined_df)
    
    # Split by Gateway
    df_with_gateway, df_without_gateway = split_by_gateway(combined_df)
    
    # Limit readings to 7 per meter per day for gateway data
    df_with_gateway_limited = limit_readings_per_day(df_with_gateway, max_readings=7)
    
    # Write to xlsx file with multiple sheets
    with pd.ExcelWriter(xlsx_path, engine='openpyxl', mode='w') as writer:
        combined_df.to_excel(writer, sheet_name='Combined', index=False)
        df_with_gateway_limited.to_excel(writer, sheet_name='With_Gateway', index=False)
        df_without_gateway.to_excel(writer, sheet_name='Without_Gateway', index=False)
    
    print(f"Data split into 3 sheets in {xlsx_path}")
    print("- Combined: All data")
    print("- With_Gateway: Meters with Gateway (max 7 readings per day)")
    print("- Without_Gateway: Meters without Gateway")

def main():
    print("Paste the path to your Excel file:")
    file_path = input().strip()
    append_all_sheets(file_path)

if __name__ == "__main__":
    main()