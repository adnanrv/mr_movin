import pandas as pd
import numpy as np
import re
import os
import sys
import time

def clean_rental_data(input_file, output_file):
    print(f"Loading data from {input_file}...")
    # Load the dataset
    df = pd.read_csv(input_file)

    # 1. Identify Metadata Columns vs Date Columns
    metadata_cols = ['RegionID', 'SizeRank', 'RegionName', 'RegionType', 'StateName']
    
    # Get all columns that are dates (formatted as YYYY-MM-DD in the CSV)
    date_cols = [col for col in df.columns if re.match(r'\d{4}-\d{2}-\d{2}', col)]
    
    print(f"Found {len(date_cols)} monthly data columns.")

    # 2. Filter for Data Starting from 2021
    years_of_interest = [2021, 2022, 2023, 2024, 2025]
    
    cleaned_df = df[metadata_cols].copy()

    print("Aggregating monthly data into annual averages...")
    
    for year in years_of_interest:
        # Find all columns for this specific year
        year_cols = [col for col in date_cols if col.startswith(str(year))]
        
        if not year_cols:
            print(f"No data found for year {year}, skipping.")
            continue
            
        # Calculate the mean for this year across the rows (axis=1)
        cleaned_df[f'{year}_Avg_Rent'] = df[year_cols].mean(axis=1).round(0)

    # 3. Data Cleaning & Formatting
    
    # Create a 'Current_Rent' column using the most recent available year
    latest_year = years_of_interest[-1] 
    while f'{latest_year}_Avg_Rent' not in cleaned_df.columns and latest_year >= 2021:
        latest_year -= 1
    
    if f'{latest_year}_Avg_Rent' in cleaned_df.columns:
        cleaned_df['Current_Rent'] = cleaned_df[f'{latest_year}_Avg_Rent']
        print(f"Using {latest_year} as the reference for Current Rent.")
    else:
        print("Warning: No recent data found to establish Current Rent.")

    # Drop rows where 'Current_Rent' is NaN
    original_count = len(cleaned_df)
    cleaned_df = cleaned_df.dropna(subset=['Current_Rent'])
    print(f"Dropped {original_count - len(cleaned_df)} regions due to missing recent rental data.")

    # Sort by SizeRank (Largest cities first)
    cleaned_df = cleaned_df.sort_values(by='SizeRank', ascending=True)

    # 5. Remove technical/unused columns as requested
    # We drop them AFTER sorting because SizeRank was used for the sort order.
    cols_to_remove = ['RegionID', 'SizeRank', 'RegionType']
    cleaned_df = cleaned_df.drop(columns=[c for c in cols_to_remove if c in cleaned_df.columns])
    print(f"Removed columns: {cols_to_remove}")

    # 4. Save to CSV and Excel
    cleaned_df.to_csv(output_file, index=False)
    print(f"Success! Cleaned data saved to CSV: {output_file}")
    
    # Save to Excel (requires openpyxl)
    output_excel = output_file.replace('.csv', '.xlsx')
    try:
        cleaned_df.to_excel(output_excel, index=False)
        print(f"Success! Cleaned data saved to Excel: {output_excel}")
    except ImportError:
        print("NOTE: Could not save Excel file. Please run 'pip install openpyxl' and try again.")
    except Exception as e:
        print(f"Could not save to Excel: {e}")

    return output_excel

def get_input_file():
    """
    Handles file input for both Google Colab and Local environments.
    """
    # Check if running in Google Colab
    try:
        import google.colab
        print("Detected Google Colab environment.")
        print("Please upload the '2 rentalMetro_zori_uc_sfr_sm_month.csv' file:")
        from google.colab import files
        uploaded = files.upload()
        if uploaded:
            return list(uploaded.keys())[0]
        else:
            return None
    except ImportError:
        # Running locally
        default_file = "2 rentalMetro_zori_uc_sfr_sm_month.csv"
        if os.path.exists(default_file):
            return default_file
        else:
            print(f"File '{default_file}' not found in current directory.")
            user_input = input("Please enter the path to your CSV file: ")
            return user_input.strip().strip('"').strip("'")

if __name__ == "__main__":
    # 1. Get the file
    input_csv = get_input_file()
    
    if input_csv:
        # Extract the filename from input path and save to data folder with same name
        input_filename = os.path.basename(input_csv)
        # Ensure data folder exists
        data_folder = "data"
        os.makedirs(data_folder, exist_ok=True)
        output_csv = os.path.join(data_folder, input_filename)
        
        try:
            # 2. Run cleaning
            excel_file = clean_rental_data(input_csv, output_csv)
            
            # 3. Auto-download results if in Colab
            try:
                import google.colab
                from google.colab import files
                print("-" * 30)
                print("ATTEMPTING DOWNLOAD...")
                print("NOTE: If the download doesn't start, check the 'Files' folder icon in the left sidebar.")
                
                files.download(output_csv)
                time.sleep(2) # Wait 2 seconds to prevent browser blocking the second download
                files.download(excel_file)
            except ImportError:
                print("-" * 30)
                print(f"Done! Files saved locally:")
                print(f"1. {output_csv}")
                print(f"2. {excel_file}")
                
        except Exception as e:
            print(f"An error occurred during processing: {e}")
    else:
        print("No file provided. Exiting.")