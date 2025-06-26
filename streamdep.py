import streamlit as st
import pandas as pd
import io
from datetime import datetime

def split_datetime_column(df, datetime_col_index=None):
    if datetime_col_index is None:
        for i, col in enumerate(df.columns):
            if pd.api.types.is_datetime64_any_dtype(df[col]) or 'time' in col.lower() or 'date' in col.lower():
                datetime_col_index = i
                break

    if datetime_col_index is not None:
        datetime_col = df.columns[datetime_col_index]
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        time_data = df[datetime_col].dt.time
        df[datetime_col] = df[datetime_col].dt.date
        time_col_name = f"{datetime_col}_time"
        df.insert(datetime_col_index + 1, time_col_name, time_data)
    return df

def limit_readings_per_day(df, max_readings=7):
    date_col = time_col = meter_col = None
    for col in df.columns:
        if 'record time' in col.lower() and 'time_time' not in col.lower():
            date_col = col
        elif 'record time_time' in col.lower() or 'time_time' in col.lower():
            time_col = col
        elif 'meter id' in col.lower() or 'meter_id' in col.lower():
            meter_col = col

    if not all([date_col, time_col, meter_col]):
        return df

    df = df.copy()
    df['temp_datetime'] = pd.to_datetime(df[date_col].astype(str) + ' ' + df[time_col].astype(str))
    df = df.sort_values([meter_col, date_col, time_col])
    filtered_rows = []

    for (meter_id, date), group in df.groupby([meter_col, date_col]):
        if len(group) <= max_readings:
            filtered_rows.append(group)
        else:
            group_copy = group.copy().reset_index(drop=True)
            while len(group_copy) > max_readings:
                time_diffs = [
                    ((group_copy.iloc[i+1]['temp_datetime'] - group_copy.iloc[i]['temp_datetime']).total_seconds() / 3600, i)
                    for i in range(len(group_copy) - 1)
                ]
                _, min_index = min(time_diffs)
                group_copy = group_copy.drop(group_copy.index[min_index + 1]).reset_index(drop=True)
            filtered_rows.append(group_copy)

    result_df = pd.concat(filtered_rows, ignore_index=True)
    return result_df.drop('temp_datetime', axis=1)

def split_by_gateway(df):
    gateway_col = next((col for col in df.columns if 'gateway' in col.lower()), None)
    if gateway_col is None:
        return df, pd.DataFrame()
    df_with_gateway = df[df[gateway_col].notna() & (df[gateway_col] != '')]
    df_without_gateway = df[df[gateway_col].isna() | (df[gateway_col] == '')]
    return df_with_gateway, df_without_gateway

def append_all_sheets(uploaded_file):
    if uploaded_file.name.endswith('.xls'):
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None, engine='xlrd')
    else:
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)

    dataframes = []
    for df in all_sheets.values():
        dataframes.append(df)
    combined_df = pd.concat(dataframes, ignore_index=True)
    combined_df = split_datetime_column(combined_df)
    df_with_gateway, df_without_gateway = split_by_gateway(combined_df)
    
    # Keep track of deleted rows for the summary
    original_with_gateway_count = len(df_with_gateway)
    df_with_gateway_limited = limit_readings_per_day(df_with_gateway)
    
    # Create summary of deleted readings
    deleted_summary = []
    if original_with_gateway_count > len(df_with_gateway_limited):
        # Group original data to see what was deleted
        meter_col = next((col for col in df_with_gateway.columns if 'meter id' in col.lower() or 'meter_id' in col.lower()), None)
        date_col = next((col for col in df_with_gateway.columns if 'record time' in col.lower() and 'time_time' not in col.lower()), None)
        
        if meter_col and date_col:
            # Count original readings per meter per day
            original_counts = df_with_gateway.groupby([meter_col, date_col]).size().reset_index(name='original_count')
            # Count final readings per meter per day
            final_counts = df_with_gateway_limited.groupby([meter_col, date_col]).size().reset_index(name='final_count')
            # Merge to see differences
            summary = pd.merge(original_counts, final_counts, on=[meter_col, date_col], how='left')
            summary['deleted_count'] = summary['original_count'] - summary['final_count']
            summary = summary[summary['deleted_count'] > 0]
            deleted_summary = summary
    
    return combined_df, df_with_gateway_limited, df_without_gateway, deleted_summary

def to_excel(combined_df, df_with_gateway_limited, df_without_gateway, deleted_summary):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        combined_df.to_excel(writer, index=False, sheet_name='TOTAL')
        df_with_gateway_limited.to_excel(writer, index=False, sheet_name='Gateway Depurado')
        df_without_gateway.to_excel(writer, index=False, sheet_name='WALKBY')
        
        # Add deleted readings summary sheet
        if len(deleted_summary) > 0:
            deleted_summary.to_excel(writer, index=False, sheet_name='Eliminado')
        else:
            # Create empty sheet with headers if no deletions
            pd.DataFrame(columns=['Meter_ID', 'Date', 'Original_Count', 'Final_Count', 'Deleted_Count']).to_excel(
                writer, index=False, sheet_name='Eliminado'
            )
    
    output.seek(0)
    return output

# === Streamlit Interface ===

st.set_page_config(page_title="Meter Excel Processor", layout="centered")

st.title("📊 Meter Excel Processor")

st.write("Upload an Excel file with multiple sheets to clean and split the data.")

uploaded_file = st.file_uploader("Upload Excel file", type=["xls", "xlsx"])

if uploaded_file:
    with st.spinner("Processing file..."):
        try:
            combined_df, df_with_gateway_limited, df_without_gateway, deleted_summary = append_all_sheets(uploaded_file)
            excel_file = to_excel(combined_df, df_with_gateway_limited, df_without_gateway, deleted_summary)
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    # Move success message and download button outside spinner
    st.success("✅ File processed successfully!")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.download_button(
            label="⬇️ Download Processed Excel",
            data=excel_file,
            file_name=f"processed_meter_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col2:
        if len(deleted_summary) > 0:
            st.info(f"📋 {len(deleted_summary)} meter-day combinations had readings reduced")
        else:
            st.info("📋 No readings were deleted")
