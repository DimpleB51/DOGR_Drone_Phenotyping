import os
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns

# Import your custom functions
from dataloader import preprocess_for_modeling # Or your equivalent preprocessing script
from models import get_model # We will only request 'random_forest'
import config as cfg # Assuming you have this for paths
import preprocess.utils as utils # Assuming get_master_df is in here

def evaluate_and_print_metrics(true_values, predicted_values, group_name):
    """Calculates and prints a standard set of regression metrics."""
    if len(true_values) < 2:
        print(f"    {group_name}: Not enough data to calculate metrics.")
        return None
    
    rmse = np.sqrt(mean_squared_error(true_values, predicted_values))
    mae = mean_absolute_error(true_values, predicted_values)
    r2 = r2_score(true_values, predicted_values)
    
    print(f"    {group_name:<28} -> RMSE: {rmse:<7.4f} | MAE: {mae:<7.4f} | R2: {r2:<7.4f}")
    return {'RMSE': rmse, 'MAE': mae, 'R2': r2}

# --- Main Script ---
if __name__ == '__main__':
    # --- 1. Load and Preprocess Data (Once) ---
    master_file_path = os.path.join(cfg.ALL_DATA_DIR, 'morphological_data', 'MASTER_DF_final.xlsx')
    
    vi_columns = ['NDVI_mean', 'NDRE_mean', 'GNDVI_mean', 'CI_RE_mean', 'SAVI_mean', 'EVI2_mean', 'LAI_mean', 'PSRI_mean', 'GLI_CUSTOM_mean', 'NORM2_mean']
    disease_columns = ['new_thrips', 'PDI_SB_new', 'PDI_PB_new', 'PDI_AN_new']

    X, y, groups = preprocess_for_modeling(
        master_df_path=master_file_path,
        vi_cols=vi_columns,
        disease_cols=disease_columns,
        biomass_proxy_col='NDVI_mean'
    )

    if X is None:
        print("Preprocessing failed. Exiting.")
        exit()

    # --- 2. Define Growth Stages and Evaluation Setup ---
    # Combine X and groups to easily filter by DAT
    df_full_features = pd.concat([X, groups], axis=1)

    growth_stages = {
        'Vegetative': (20, 50),
        'Bulb Initiation': (51, 70),
        'Bulb Development': (71, np.inf)
    }

    # Dictionary to store results for each stage's model
    stage_based_results = {}

    # --- 3. Loop Through Each Growth Stage to Train a Separate Model ---
    for stage_name, (start_dat, end_dat) in growth_stages.items():
        print(f"\n{'='*25} TRAINING MODEL FOR STAGE: {stage_name.upper()} (DAT {start_dat}-{end_dat}) {'='*25}")
        
        # --- a) Filter data for the current stage ---
        stage_mask = (df_full_features['DAT'] >= start_dat) & (df_full_features['DAT'] <= end_dat)
        X_stage = X[stage_mask].copy()
        y_stage = y[stage_mask].copy()
        groups_stage = groups[stage_mask].copy()

        if len(X_stage) < 10: # Check if there's enough data to even bother
            print(f"Not enough data ({len(X_stage)} points) for stage '{stage_name}'. Skipping.")
            continue
        
        print(f"Data points in this stage: {len(X_stage)}")
        
        stage_model_scores_per_target = {}

        # --- b) Loop through each target variable ---
        for target_col in y_stage.columns:
            print(f"\n--- Training for Target: {target_col} ---")
            
            y_current = y_stage[target_col]
            
            # Lists to store metrics from each fold for this stage's model
            fold_metrics = {'rmse': [], 'mae': [], 'r2': []}
            
            # Use GroupKFold on the subset of data for this stage
            group_kfold = GroupKFold(n_splits=3)
            # Pass the replication groups for this specific stage subset
            stage_replication_groups = groups_stage['Replication']
            
            for fold, (train_idx, val_idx) in enumerate(group_kfold.split(X_stage, y_current, groups=stage_replication_groups)):
                X_train, X_val = X_stage.iloc[train_idx], X_stage.iloc[val_idx]
                y_train, y_val = y_current.iloc[train_idx], y_current.iloc[val_idx]

                # Get a new RandomForest model for each fold
                model = get_model('random_forest')
                if model is None:
                    print("Could not create RandomForest model. Skipping.")
                    break

                model.fit(X_train, y_train)
                predictions = model.predict(X_val)
                
                fold_metrics['rmse'].append(np.sqrt(mean_squared_error(y_val, predictions)))
                fold_metrics['mae'].append(mean_absolute_error(y_val, predictions))
                fold_metrics['r2'].append(r2_score(y_val, predictions))
            
            if model is None: continue

            # --- c) Aggregate and store results for this target and stage ---
            avg_rmse = np.mean(fold_metrics['rmse'])
            avg_mae = np.mean(fold_metrics['mae'])
            avg_r2 = np.mean(fold_metrics['r2'])
            
            stage_model_scores_per_target[target_col] = {
                'RMSE': avg_rmse, 'MAE': avg_mae, 'R2': avg_r2
            }
            
            print(f"--- Avg CV Results for {target_col} in '{stage_name}' stage:")
            print(f"  RMSE: {avg_rmse:.4f} | MAE: {avg_mae:.4f} | R2: {avg_r2:.4f}")

        stage_based_results[stage_name] = stage_model_scores_per_target

    # --- 4. Final Summary Printout ---
    print("\n\n" + "="*80)
    print("           STAGE-BASED RANDOM FOREST MODEL PERFORMANCE SUMMARY")
    print("="*80)

    for stage_name, target_data in stage_based_results.items():
        print(f"\n--- PERFORMANCE FOR: {stage_name.upper()} STAGE MODEL ---")
        # Convert to DataFrame for nice printing
        results_df = pd.DataFrame(target_data).T # Transpose to have targets as rows
        print(results_df)

    print("\n" + "="*80)