import os
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold, train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
import lightgbm as lgb
import warnings

# Import your custom functions
from dataloader import preprocess_for_modeling
from models import get_model
import config as cfg

def evaluate_and_print_metrics(true_values, predicted_values, group_name):
    """Calculates and prints a standard set of regression metrics."""
    if len(true_values) < 2:
        print(f"    {group_name}: Not enough data to calculate metrics.")
        return None
    
    rmse = np.sqrt(mean_squared_error(true_values, predicted_values))
    mae = mean_absolute_error(true_values, predicted_values)
    r2 = r2_score(true_values, predicted_values)
    
    print(f"    {group_name:<15} -> RMSE: {rmse:<7.4f} | MAE: {mae:<7.4f} | R2: {r2:<7.4f}")
    return {'RMSE': rmse, 'MAE': mae, 'R2': r2}

# --- Main Script ---
if __name__ == '__main__':
    # --- 1. Load and Preprocess Data ---
    master_file_path = os.path.join(cfg.ALL_DATA_DIR, 'master_sheet.xlsx')
    
    vi_columns = [
                #   'NDVI_mean', 
                #'NDRE_mean', 'GNDVI_mean', 'CI_RE_mean', 'SAVI_mean', 'EVI2_mean', 
                
                'RHdelta',	'temp_curr_day', 'RH_curr_day',	'rain_curr_day', 'rain_total_day', 'max_temp_prevday', 	'total_rain_prevday',	'max_temp_last_7days', 	'avg_RH_last_7days', 'avg_rain_last_7days'
                #   'LAI_mean', 
                #   'PSRI_mean', 'GLI_CUSTOM_mean', 'NORM2_mean'
                ]
    disease_columns = [
        # 'new_thrips', 
        'PDI_SB_new', 
        # 'PDI_PB_new', 
        # 'PDI_AN_new'
        ]

    X, y, groups = preprocess_for_modeling(
        master_df_path=master_file_path,
        vi_cols=vi_columns,
        disease_cols=disease_columns,
        biomass_proxy_col='NDVI_mean'
    )

   # Create a boolean mask from the relevant column in X
    # This mask will be True for rows belonging to the Kharif season
    # kharif_filter_mask = (X['Season_Kharif'] == 1) & (X['DAT'] > 0)
    filter_mask = (groups['Treatment'] == 'T4')

    # Apply this same boolean mask to filter the ROWS of all three DataFrames
    X_kharif = X[filter_mask].copy()
    y_kharif = y[filter_mask].copy()
    groups_kharif = groups[filter_mask].copy()


    if X is None:
        print("Preprocessing failed. Exiting.")
        exit()

    # --- 2. Define Models and Evaluation Setup ---
    models_to_try = [
        # 'lightgbm',
        'random_forest',
        'ridge',
        # 'glmnet',
        'svr'
    ]

    # Define growth stages based on DAT
    stage_bins = [20, 50, 70, np.inf] # Bins for <50, 50-70, >70
    stage_labels = ['Vegetative (20-50 DAT)', 'Bulb Initiation (51-70 DAT)', 'Bulb Development (>70 DAT)']

    all_model_predictions = {} # Store predictions for plotting

    y = y_kharif
    X = X_kharif
    groups = groups_kharif
    # --- 3. Loop Through Models and Perform Cross-Validation ---
    for model_name in models_to_try:
        print(f"\n{'='*25} TESTING MODEL: {model_name.upper()} {'='*25}")
        
        model_predictions_per_target = {}

        for target_col in y.columns:
            print(f"\n--- Training for Target: {target_col} ---")
            
            y_current = y[target_col]
            all_fold_predictions_df = pd.DataFrame()
            
            group_kfold = GroupKFold(n_splits=3)
            for fold, (train_idx, val_idx) in enumerate(group_kfold.split(X, y_current, groups=groups['Replication'])):
                X_train_full, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train_full, y_val = y_current.iloc[train_idx], y_current.iloc[val_idx]

                model = get_model(model_name)
                if model is None:
                    warnings.warn(f"Could not create model '{model_name}'. Skipping.")
                    break

                if model_name == 'lightgbm':
                    X_train, X_eval, y_train, y_eval_lgbm = train_test_split(X_train_full, y_train_full, test_size=0.2, random_state=42)
                    model.fit(X_train, y_train,
                              eval_set=[(X_eval, y_eval_lgbm)],
                              eval_metric='rmse',
                              callbacks=[lgb.early_stopping(20, verbose=False)])
                else:
                    model.fit(X_train_full, y_train_full)
                
                predictions = model.predict(X_val)
                
                season_cols = [col for col in X_val.columns if 'Season_' in col]
                reconstructed_season = X_val[season_cols].idxmax(axis=1).str.replace('Season_', '') if season_cols else 'Unknown'

                fold_pred_df = pd.DataFrame({
                    'True': y_val.values,
                    'Predicted': predictions,
                    'Season': reconstructed_season,
                    'DAT': X_val['DAT'].values
                })
                all_fold_predictions_df = pd.concat([all_fold_predictions_df, fold_pred_df], ignore_index=True)
            
            if model is None: continue
            
            model_predictions_per_target[target_col] = all_fold_predictions_df
        
        all_model_predictions[model_name] = model_predictions_per_target

    # --- 4. Detailed Performance Evaluation (Overall, Seasonal, and Growth Stage) ---
    print("\n\n" + "="*80)
    print("           DETAILED MODEL PERFORMANCE EVALUATION")
    print("="*80)

    for model_name, predictions_by_target in all_model_predictions.items():
        print(f"\n\n--- MODEL: {model_name.upper()} ---")
        for target_col, pred_df in predictions_by_target.items():
            print(f"\n  Target: {target_col}")
            
            # a) Overall Performance
            print("  - Overall Performance:")
            evaluate_and_print_metrics(pred_df['True'], pred_df['Predicted'], "All Data")

            # b) Seasonal Performance
            print("\n  - Seasonal Performance:")
            for season in sorted(pred_df['Season'].unique()):
                season_df = pred_df[pred_df['Season'] == season]
                evaluate_and_print_metrics(season_df['True'], season_df['Predicted'], f"Season: {season}")

            # c) Growth Stage Performance
            print("\n  - Growth Stage Performance:")
            # Use pd.cut to assign each row to a growth stage bin
            pred_df['Growth_Stage'] = pd.cut(pred_df['DAT'], bins=stage_bins, labels=stage_labels, right=False)
            for stage in stage_labels:
                stage_df = pred_df[pred_df['Growth_Stage'] == stage]
                evaluate_and_print_metrics(stage_df['True'], stage_df['Predicted'], f"Stage: {stage}")
    print("\n" + "="*80)

    # --- 5. Plot True vs. Predicted Values Over DAT ---
    print("\n\n--- Generating True vs. Predicted Plots ---")
    
    for model_name, predictions_by_target in all_model_predictions.items():
        n_targets = len(predictions_by_target)
        if n_targets == 0: continue
        
        fig, axes = plt.subplots(n_targets, 1, figsize=(14, n_targets * 6), sharex=True, layout='constrained')
        if n_targets == 1:
            axes = [axes]

        fig.suptitle(f'True vs. Predicted Values for Model: {model_name.upper()}', fontsize=20, y=1.03)

        for i, (target_col, pred_df) in enumerate(predictions_by_target.items()):
            ax = axes[i]
    
            # --- Step 1: Explicitly calculate the mean of True and Predicted values for each DAT ---
            # This removes any ambiguity about what the lineplot is doing.
            plot_data = pred_df.groupby('DAT').agg(
                Mean_True=('True', 'mean'),
                Mean_Predicted=('Predicted', 'mean')
            ).reset_index()

            # --- Step 2: Plot the aggregated means ---
            # Now we plot the lines connecting the means
            ax.plot(plot_data['DAT'], plot_data['Mean_True'], label='Mean True Value', color='dodgerblue', marker='o', linewidth=2.5, zorder=10)
            ax.plot(plot_data['DAT'], plot_data['Mean_Predicted'], label='Mean Predicted Value', color='red', linestyle='--', marker='x', zorder=10)

            # --- Step 3 (Optional but Recommended): Plot the individual raw points as a scatter plot ---
            # This shows the underlying spread of data that the mean lines are summarizing.
            sns.scatterplot(data=pred_df, x='DAT', y='True', ax=ax, color='dodgerblue', alpha=0.2, legend=False, zorder=5)
            sns.scatterplot(data=pred_df, x='DAT', y='Predicted', ax=ax, color='red', alpha=0.2, legend=False, marker='x', zorder=5)
            # Calculate overall metrics for this target
            overall_metrics = evaluate_and_print_metrics(pred_df['True'], pred_df['Predicted'], "")
            
            # Add metrics text to the plot
            if overall_metrics:
                metrics_text = f"RMSE: {overall_metrics['RMSE']:.4f}\nMAE: {overall_metrics['MAE']:.4f}\nR²: {overall_metrics['R2']:.4f}"
                ax.text(0.02, 0.98, metrics_text, transform=ax.transAxes, fontsize=11, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            ax.set_title(f'Target: {target_col}', fontsize=16)
            ax.set_ylabel('Value', fontsize=12)
            ax.set_ylim((0, 1))
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()
        
        axes[-1].set_xlabel('Days After Transplanting (DAT)', fontsize=14)
        
        plt.show()
        fig.savefig(f"{model_name}_true_vs_predicted_t4---.png", dpi=150, bbox_inches='tight')