import pandas as pd
import numpy as np
import os
import config as cfg
from src.preprocess import utils as utils

def preprocess_for_modeling(master_df_path, vi_cols, disease_cols, biomass_proxy_col='NDVI_mean'):
    """
    Loads master data, performs feature engineering (ratios and deltas),
    and selects final features and targets for modeling.

    Args:
        master_df_path (str): Path to the master Excel file with all trials.
        vi_cols (list): List of base VI column names to use (e.g., ['NDVI_mean', 'NDRE_mean']).
        disease_cols (list): List of disease/pest column names.
        biomass_proxy_col (str, optional): The VI column to use as the denominator
                                           for ratio features. Defaults to 'NDVI_mean'.

    Returns:
        tuple: A tuple containing:
            - pd.DataFrame: X_final (the final features for modeling).
            - pd.DataFrame: y_final (the final targets for modeling).
            - pd.DataFrame: group_identifiers (columns like Trial_ID, Replication for splitting).
    """
    print("--- Starting Data Preprocessing for Modeling ---")

    # --- 1. Load and Combine All Trial Data ---
    # Assuming get_master_df is defined elsewhere and can concatenate all sheets
    df_full = utils.get_master_df(master_df_path, concat_all=True, log=False)
    # Convert Trial_ID column to have zero-padded format (01-09 instead of 1-9)
    if 'Trial_ID' in df_full.columns:
        df_full['Trial_ID'] = df_full['Trial_ID'].str.replace('Trial', '')
    if df_full.empty:
        print("Master DataFrame is empty. Exiting.")
        return None, None, None

    print(f"Loaded and concatenated all trials. Initial shape: {df_full.shape}")

    # --- 2. Data Cleaning and Type Conversion ---
    # Ensure DAT is numeric
    if 'DAT' not in df_full.columns:
        raise KeyError("Required column 'DAT' not found in the DataFrame.")
    df_full['DAT'] = pd.to_numeric(df_full['DAT'], errors='coerce')

    # Ensure all feature/target columns are numeric
    cols_to_convert = vi_cols + disease_cols
    for col in cols_to_convert:
        if col in df_full.columns:
            df_full[col] = pd.to_numeric(df_full[col], errors='coerce')
        else:
            print(f"Warning: Column '{col}' not found in DataFrame. It will be skipped.")
    
    print(df_full.shape)
    # Drop rows with missing essential data like DAT
    df_full.dropna(subset=['DAT'], inplace=True)
    # Print rows where DAT is missing before dropping them
    missing_dat_rows = df_full[df_full['DAT'].isna()]
    if not missing_dat_rows.empty:
        print(f"Found {len(missing_dat_rows)} rows with missing DAT values:")
        print(missing_dat_rows[['Trial_ID', 'Replication', 'Treatment']].drop_duplicates())
    else:
        print("No rows with missing DAT values found.")
    print(df_full.shape)
    # --- 3. Feature Engineering ---
    print("Starting feature engineering...")
    
    # Sort data for time-series operations
    # Crucial for calculating deltas correctly for each unique plot
    df_full.sort_values(by=['Trial_ID', 'Replication', 'Treatment', 'DAT'], inplace=True)

    # --- NEW: Add Lagged Features (Previous Time Step's Values) ---
    print("    Creating lagged features...")
    # Define which columns to create lags for
    cols_to_lag = [col for col in (vi_cols + disease_cols) if col in df_full.columns]
    
    # Group by each individual plot and shift to get the previous value
    lagged_df = df_full.groupby(['Trial_ID', 'Replication', 'Treatment'])[cols_to_lag].shift(1)
    lagged_df.columns = [f"{col}_lag1" for col in lagged_df.columns]
    
    # Join the lagged features back to the main dataframe
    df_full = df_full.join(lagged_df)
    # --- NEW: Add Rolling Window Statistics (Recent Trend and Volatility) ---
    print("    Creating rolling window features...")
    # Define a window size (e.g., 2 for the last two points, 3 for the last three)
    window_size = 2
    
    # Define which columns to get rolling stats for (usually just VIs)
    cols_for_rolling = [col for col in vi_cols if col in df_full.columns]
    
    # Group by each plot and apply rolling window operations
    grouped = df_full.groupby(['Trial_ID', 'Replication', 'Treatment'])[cols_for_rolling]
    
    # Calculate rolling mean and standard deviation
    rolling_mean = grouped.rolling(window=window_size, min_periods=window_size).mean()
    rolling_std = grouped.rolling(window=window_size, min_periods=window_size).std()
    
    # The output of rolling is multi-indexed, so we need to drop the group keys to align it
    rolling_mean = rolling_mean.reset_index(level=[0, 1, 2], drop=True)
    rolling_std = rolling_std.reset_index(level=[0, 1, 2], drop=True)
    
    # Add suffixes to the new column names
    rolling_mean.columns = [f"{col}_roll_mean{window_size}" for col in rolling_mean.columns]
    rolling_std.columns = [f"{col}_roll_std{window_size}" for col in rolling_std.columns]
    
    # Join the new rolling features back to the main dataframe
    df_full = df_full.join(rolling_mean)
    df_full = df_full.join(rolling_std)

    # a) Create Delta (Rate of Change) Features
    delta_cols_to_calculate = [col for col in vi_cols if col in df_full.columns]
    delta_df = df_full.groupby(['Trial_ID', 'Replication', 'Treatment'])[delta_cols_to_calculate].diff()
    delta_df.columns = [f"{col}_delta" for col in delta_df.columns]
    
    # b) Create Ratio (Biomass-Normalized) Features
    ratio_df = pd.DataFrame(index=df_full.index) # Create an empty df with same index
    if biomass_proxy_col in df_full.columns:
        for col in vi_cols:
            if col in df_full.columns and col != biomass_proxy_col:
                new_col_name = f"{col}_div_{biomass_proxy_col.split('_')[0]}"
                # Use np.where to avoid division by zero or by small, noisy NDVI values
                ratio_df[new_col_name] = np.where(
                    df_full[biomass_proxy_col] > 0.1, # Threshold to ensure it's vegetation
                    df_full[col] / df_full[biomass_proxy_col],
                    np.nan # Result is NaN if biomass proxy is too low
                )
    
    # c) One-Hot Encode Seasonal Information
    # Create season mapping based on trial
    season_map = {
        '1': 'Kharif',
        '2': 'Kharif', 
        '3': 'Kharif',
        '4': 'Kharif',
        '5': 'Kharif',
        '6': 'LateKharif',
        '7': 'LateKharif',
        '8': 'Rabi',
        '9': 'Rabi',
        '10': 'Rabi',
        '11': 'Rabi',
        '12': 'Rabi'
    }
    
    # Create Season column based on Trial_ID mapping
    df_full['Season'] = df_full['Trial_ID'].map(season_map)
    
    # Create one-hot encoded season features
    if 'Season' in df_full.columns and df_full['Season'].notna().any():
        season_dummies = pd.get_dummies(df_full['Season'], prefix='Season', dtype=int)
    else:
        print("Warning: Season column could not be created or contains only NaN values.")
        season_dummies = pd.DataFrame()


    # --- 4. Combine All Features and Targets into a Final DataFrame ---
    # Use reset_index().join() for robust concatenation
    df_processed = df_full.reset_index(drop=True).join([delta_df, ratio_df])
    df_processed = pd.concat([df_processed, season_dummies], axis=1)
    
    print(f"Feature engineering complete. DataFrame shape: {df_processed.shape}")
    
    # --- 5. Prepare Final Feature Matrix (X) and Target Matrix (y) ---
    
    # Define final features to keep for the model
    # These are selected based on our EDA insights
    final_feature_cols = [
        'DAT', # Time is a crucial feature
        'NDVI_mean'
    ]
    # Add ratio features
    final_feature_cols.extend([col for col in df_processed.columns if '_div_' in col])
    # Add delta features
    final_feature_cols.extend([col for col in df_processed.columns if '_delta' in col])
    # --- NEW: Add Lagged and Rolling Features ---
    final_feature_cols.extend([col for col in df_processed.columns if '_lag1' in col])
    final_feature_cols.extend([col for col in df_processed.columns if '_roll_' in col])
    
    # Add one-hot encoded season features
    final_feature_cols.extend([col for col in df_processed.columns if 'Season_' in col])
    
    # Filter out columns that might not exist if source data was incomplete
    final_feature_cols = [col for col in final_feature_cols if col in df_processed.columns]
    
    print(f"\nFinal selected features for model ({len(final_feature_cols)}): {final_feature_cols}")
    
    # Define final target variables
    final_target_cols = []
    # a) Normalize PDI columns (0-100 -> 0-1)
    for col in disease_cols:
        if 'PDI' in col and col in df_processed.columns:
            new_target_name = f"{col}_norm"
            df_processed[new_target_name] = df_processed[col] / 100.0
            final_target_cols.append(new_target_name)
            
    # b) Log-transform thrips count
    thrips_col = 'new_thrips'
    if thrips_col in disease_cols and thrips_col in df_processed.columns:
        new_target_name = f"{thrips_col}_log"
        df_processed[new_target_name] = np.log1p(df_processed[thrips_col])
        final_target_cols.append(new_target_name)

    print(f"Final transformed targets for model ({len(final_target_cols)}): {final_target_cols}")

    # --- 6. Select and Clean Final DataFrames ---
    # Columns needed for grouping/identification
    group_id_cols = ['Trial_ID', 'Replication', 'Treatment']
    
    # Select only the necessary columns
    final_df_subset = df_processed[group_id_cols + final_feature_cols + final_target_cols]
    
    # Drop rows where any of the final features or targets are NaN
    # This is important because the delta calculation created NaNs for the first time point of each plot
    final_df_clean = final_df_subset.dropna(subset=final_feature_cols + final_target_cols).reset_index(drop=True)
    
    print(f"\nShape after dropping all NaNs from features/targets: {final_df_clean.shape}")

    # Separate into X, y, and groups
    X_final = final_df_clean[final_feature_cols]
    y_final = final_df_clean[final_target_cols]
    group_identifiers = final_df_clean[group_id_cols]
    
    return X_final, y_final, group_identifiers


# --- Example Usage ---
if __name__ == '__main__':
    # Assume get_master_df and cfg are defined
    import config as cfg

    master_file_path = os.path.join(cfg.ALL_DATA_DIR, 'morphological_data', 'MASTER_DF_final.xlsx')
    
    # Define the base VIs and diseases to process
    vi_columns = ['NDVI_mean', 'NDRE_mean', 'GNDVI_mean', 'CI_RE_mean', 'SAVI_mean', 'EVI2_mean', 'LAI_mean', 'PSRI_mean', 'GLI_CUSTOM_mean', 'NORM2_mean']
    disease_columns = ['new_thrips', 'PDI_SB_new', 'PDI_PB_new', 'PDI_AN_new']

    # Run the preprocessing pipeline
    X, y, groups = preprocess_for_modeling(
        master_file_path,
        vi_cols=vi_columns,
        disease_cols=disease_columns,
        biomass_proxy_col='NDVI_mean'
    )

    if X is not None:
        print("\n--- Preprocessing Complete ---")
        print("\nFeatures (X) head:")
        print(X.head())
        print(f"\nFeatures shape: {X.shape}")
        
        print("\nTargets (y) head:")
        print(y.head())
        print(f"\nTargets shape: {y.shape}")
        
        print("\nGroup Identifiers head:")
        print(groups.head())
        print(f"\nGroups shape: {groups.shape}")