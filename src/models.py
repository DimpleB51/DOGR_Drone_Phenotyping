# models.py

import warnings

try:
    import lightgbm as lgb
except ImportError:
    warnings.warn("LightGBM is not installed. LGBMRegressor will not be available.")
    lgb = None

try:
    import xgboost as xgb
except ImportError:
    warnings.warn("XGBoost is not installed. XGBRegressor will not be available.")
    xgb = None

# New imports for SVR and ElasticNet (GLMNET)
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

def get_model(model_name: str, multi_output_wrapper: bool = False, **kwargs):
    """
    Model factory to get an initialized regression model instance.

    Args:
        model_name (str): The name of the model to get.
                          Supported: 'ridge', 'lasso', 'glmnet', 'random_forest',
                          'svr', 'lightgbm', 'xgboost'.
        multi_output_wrapper (bool): If True, wraps the model in scikit-learn's
                                     MultiOutputRegressor. Defaults to False.
        **kwargs: Additional keyword arguments to pass to the model's constructor.

    Returns:
        An initialized scikit-learn compatible regressor model, or None if the
        model name is not recognized or its library is not installed.
    """
    model_name = model_name.lower()
    
    # --- Model Selection with Specific Defaults ---
    
    if model_name == 'ridge':
        # Linear models like Ridge benefit from feature scaling
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('ridge', Ridge(random_state=42, **kwargs))
        ])
        
    elif model_name == 'lasso':
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('lasso', Lasso(random_state=42, **kwargs))
        ])

    elif model_name == 'glmnet':
        # GLMNET is implemented as ElasticNet in scikit-learn
        # It combines L1 (Lasso) and L2 (Ridge) penalties.
        # alpha is the overall strength of regularization.
        # l1_ratio controls the mix: 1.0 is Lasso, 0.0 is Ridge.
        default_params = {'alpha': 1.0, 'l1_ratio': 0.5}
        default_params.update(kwargs)
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('glmnet', ElasticNet(random_state=42, **default_params))
        ])
        
    elif model_name == 'random_forest':
        default_params = {
            'n_estimators': 1000,
            'max_depth': 7,
            'min_samples_split': 2,
            'min_samples_leaf': 1,
            'n_jobs': -1,
            'random_state': 42
        }
        default_params.update(kwargs)
        model = RandomForestRegressor(**default_params)
        
    elif model_name == 'svr':
        # Support Vector Regressor is very sensitive to feature scaling
        # We use a Pipeline to automatically scale the data before fitting SVR
        # Common kernels are 'rbf', 'linear', 'poly'
        default_params = {'kernel': 'rbf', 'C': 1.0, 'epsilon': 0.1}
        default_params.update(kwargs)
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('svr', SVR(**default_params))
        ])
        
    elif model_name == 'lightgbm':
        if lgb:
            default_params = {
                'n_estimators': 500, 'learning_rate': 0.05,
                'num_leaves': 20, 'max_depth': -1,
                'min_child_samples': 10, 'n_jobs': -1,
                'random_state': 42, 'verbosity': -1
            }
            default_params.update(kwargs)
            model = lgb.LGBMRegressor(**default_params)
        else:
            print("LightGBM model requested but library is not installed. Returning None.")
            return None
            
    elif model_name == 'xgboost':
        if xgb:
            default_params = {
                'n_estimators': 500, 'learning_rate': 0.05,
                'max_depth': 5, 'n_jobs': -1,
                'random_state': 42
            }
            default_params.update(kwargs)
            model = xgb.XGBRegressor(**default_params)
        else:
            print("XGBoost model requested but library is not installed. Returning None.")
            return None
            
    else:
        raise ValueError(f"Model '{model_name}' not recognized. "
                         "Supported models: 'ridge', 'lasso', 'glmnet', 'random_forest', "
                         "'svr', 'lightgbm', 'xgboost'.")

    # --- Multi-Output Wrapper ---
    if multi_output_wrapper:
        print(f"Wrapping {model_name} model with MultiOutputRegressor.")
        return MultiOutputRegressor(model)
    else:
        return model

# --- Example Usage ---
if __name__ == '__main__':
    print("--- Testing Model Factory ---")
    
    print("\n1. Getting an SVR model (will be wrapped in a Pipeline):")
    svr_model = get_model('svr', C=10) # Pass custom SVR parameter
    if svr_model:
        print(f"   Successfully created model pipeline: {svr_model}")
        print(f"   SVR C parameter: {svr_model.named_steps['svr'].C}")

    print("\n2. Getting a GLMNET (ElasticNet) model:")
    glmnet_model = get_model('glmnet', alpha=0.1, l1_ratio=0.7)
    if glmnet_model:
        print(f"   Successfully created model pipeline: {glmnet_model}")
        print(f"   ElasticNet alpha: {glmnet_model.named_steps['glmnet'].alpha}")
        print(f"   ElasticNet l1_ratio: {glmnet_model.named_steps['glmnet'].l1_ratio}")

    print("\n3. Getting a multi-output wrapped LightGBM model:")
    lgbm_multi_model = get_model('lightgbm', multi_output_wrapper=True)
    if lgbm_multi_model:
        print(f"   Successfully created model: {lgbm_multi_model.__class__.__name__}")
        print(f"   Underlying estimator: {lgbm_multi_model.estimator}")