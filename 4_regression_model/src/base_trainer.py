import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split # Changed import
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
    
    print(f"    {group_name:<28} -> RMSE: {rmse:<7.4f} | MAE: {mae:<7.4f} | R2: {r2:<7.4f}")
    return {'RMSE': rmse, 'MAE': mae, 'R2': r2}

# --- Main Script ---
if __name__ == '__main__':
    # --- 1. Load and Preprocess Data ---
    master_file_path = os.path.join(cfg.ALL_DATA_DIR, 'morphological_data', 'MASTER_DF_final.xlsx')
    
    vi_columns = [
        'NDVI_mean', 'NDRE_mean', 'GNDVI_mean', 'CI_RE_mean', 'SAVI_mean', 'EVI2_mean', 'LAI_mean', 
        #'PSRI_mean', 'GLI_CUSTOM_mean', 'NORM2_mean'
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
    X = X[X['DAT'] > 25]
    y = y[y.index.isin(X.index)]  # Ensure y matches X after filtering
    groups = groups[groups.index.isin(X.index)]  # Ensure groups matches X after filtering
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

    stage_bins = [0, 50, 70, np.inf]
    stage_labels = ['Vegetative (<50 DAT)', 'Bulb Initiation (51-70 DAT)', 'Bulb Development (>70 DAT)']

    all_model_predictions = {}

    # --- 3. Loop Through Models, Performing a Single Train/Test Split ---
    for model_name in models_to_try:
        print(f"\n{'='*25} TESTING MODEL: {model_name.upper()} {'='*25}")
        
        model_predictions_per_target = {}

        for target_col in y.columns:
            print(f"\n--- Training for Target: {target_col} ---")
            
            y_current = y[target_col]
            
            # --- MODIFICATION: Use train_test_split instead of GroupKFold ---
            # Perform a single, random 80/20 split of the entire dataset.
            X_train, X_test, y_train, y_test, groups_train, groups_test = train_test_split(
                X, 
                y_current, 
                groups, # Also split the groups DataFrame to get DAT/Season for the test set
                test_size=0.2, 
                random_state=42 # For reproducibility
            )
            # --- END OF MODIFICATION ---
            
            print(f"Train set size: {len(X_train)}, Test set size: {len(X_test)}")

            model = get_model(model_name)
            if model is None:
                warnings.warn(f"Could not create model '{model_name}'. Skipping.")
                continue

            # Fit model (early stopping requires a separate eval set from the train set)
            if model_name == 'lightgbm':
                X_train_lgbm, X_eval_lgbm, y_train_lgbm, y_eval_lgbm = train_test_split(X_train, y_train, test_size=0.2, random_state=42)
                model.fit(X_train_lgbm, y_train_lgbm,
                          eval_set=[(X_eval_lgbm, y_eval_lgbm)],
                          eval_metric='rmse',
                          callbacks=[lgb.early_stopping(20, verbose=False)])
            else:
                model.fit(X_train, y_train)
            
            predictions = model.predict(X_test)
            
            # --- Store true values, predictions, and identifiers for plotting/evaluation ---
            # Reconstruct season from one-hot encoded columns in the test set features
            season_cols = [col for col in X_test.columns if 'Season_' in col]
            reconstructed_season = X_test[season_cols].idxmax(axis=1).str.replace('Season_', '') if season_cols else 'Unknown'

            predictions_df = pd.DataFrame({
                'True': y_test.values,
                'Predicted': predictions,
                'Season': reconstructed_season,
                'DAT': X_test['DAT'].values
            })
            
            model_predictions_per_target[target_col] = predictions_df
        
        all_model_predictions[model_name] = model_predictions_per_target

    # --- 4. Detailed Performance Evaluation (on the single test set) ---
    print("\n\n" + "="*80)
    print("           DETAILED MODEL PERFORMANCE EVALUATION (on 20% Random Test Set)")
    print("="*80)

    for model_name, predictions_by_target in all_model_predictions.items():
        print(f"\n\n--- MODEL: {model_name.upper()} ---")
        for target_col, pred_df in predictions_by_target.items():
            print(f"\n  Target: {target_col}")
            
            print("  - Overall Performance on Test Set:")
            evaluate_and_print_metrics(pred_df['True'], pred_df['Predicted'], "Test Set")

            print("\n  - Seasonal Performance on Test Set:")
            for season in sorted(pred_df['Season'].unique()):
                season_df = pred_df[pred_df['Season'] == season]
                evaluate_and_print_metrics(season_df['True'], season_df['Predicted'], f"Season: {season}")

            print("\n  - Growth Stage Performance on Test Set:")
            pred_df['Growth_Stage'] = pd.cut(pred_df['DAT'], bins=stage_bins, labels=stage_labels, right=False)
            for stage in stage_labels:
                stage_df = pred_df[pred_df['Growth_Stage'] == stage]
                evaluate_and_print_metrics(stage_df['True'], stage_df['Predicted'], f"Stage: {stage}")
    print("\n" + "="*80)

    # --- 5. Plot True vs. Predicted Values Over DAT (on the single test set) ---
    print("\n\n--- Generating True vs. Predicted Plots ---")
    
    for model_name, predictions_by_target in all_model_predictions.items():
        n_targets = len(predictions_by_target)
        if n_targets == 0: continue
        
        fig, axes = plt.subplots(n_targets, 1, figsize=(14, n_targets * 6), sharex=True, layout='constrained')
        if n_targets == 1: axes = [axes]

        fig.suptitle(f'True vs. Predicted Values for Model: {model_name.upper()}', fontsize=20, y=1.03)

        for i, (target_col, pred_df) in enumerate(predictions_by_target.items()):
            ax = axes[i]
    
            plot_data = pred_df.groupby('DAT').agg(
                Mean_True=('True', 'mean'),
                Mean_Predicted=('Predicted', 'mean')
            ).reset_index()

            ax.plot(plot_data['DAT'], plot_data['Mean_True'], label='Mean True Value', color='dodgerblue', marker='o', linewidth=2.5, zorder=10)
            ax.plot(plot_data['DAT'], plot_data['Mean_Predicted'], label='Mean Predicted Value', color='red', linestyle='--', marker='x', zorder=10)

            sns.scatterplot(data=pred_df, x='DAT', y='True', ax=ax, color='dodgerblue', alpha=0.2, legend=False, zorder=5)
            sns.scatterplot(data=pred_df, x='DAT', y='Predicted', ax=ax, color='red', alpha=0.2, legend=False, marker='x', zorder=5)

            ax.set_title(f'Target: {target_col}', fontsize=16)
            ax.set_ylabel('Value', fontsize=12)
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()
        
        axes[-1].set_xlabel('Days After Transplanting (DAT)', fontsize=14)
        
        plt.show()
        fig.savefig(f"{model_name}_true_vs_predicted_random_split.png", dpi=150, bbox_inches='tight')