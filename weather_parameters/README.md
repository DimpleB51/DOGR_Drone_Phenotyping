# 🌱 Weather-Based Classification of Thrips and Diseases in Onion Plants

Great! Since you have **high-resolution (15-minute interval)** weather station data and are working on classifying **thrips**, **blight**, **blotch**, and **anthracnose** in onion plants, you're in a strong position to **engineer biologically meaningful features** and build an effective classification model.

---

## ✅ Step 1: Organize Your Input Data

**Expected format:**
- `Timestamp` (15-min intervals)
- `Temperature (°C)`
- `Relative Humidity (%)`
- `Rainfall (mm)`
- `Disease/Thrips Labels` (e.g., per day or per plot)

> 🔑 **Key:** Align your labels (disease/thrips) with the **date** or **plot ID**.

---

## ✅ Step 2: Create Aggregated Features by Time Blocks

Use the following **4 core time blocks**, plus **pre-8 AM** for fungal diseases:

| Block Name     | Time Range      | Reason                                             |
|----------------|------------------|----------------------------------------------------|
| **Pre-Morning**| 4:00–8:00 AM     | Leaf wetness / dew (fungal triggers)               |
| **Morning 1**  | 8:00–10:00 AM    | Fungal spores, thrips begin activity               |
| **Morning 2**  | 10:00–12:00 PM   | Temp rises, RH drops, thrips active                |
| **Midday**     | 12:00–2:00 PM    | Max heat stress, anthracnose risk                  |
| **Afternoon**  | 2:00–4:00 PM     | Thrips re-activity if heat drops                   |

---

## ✅ Step 3: Feature Engineering (Per Block)

For **each block per day**, extract the following:

### 🌡 Temperature
- Mean temperature
- Max temperature
- Temperature delta (block-wise change)

### 💧 Relative Humidity
- Mean RH
- Duration where RH > 90% (proxy for wetness)
- Drop in RH between Pre-Morning and Midday (drying rate)

### 🌧 Rainfall
- Rainfall sum per block
- Total rainfall in past 24–48 hours (cumulative lag)
- Rainfall > 0.5 mm in pre-8 AM (binary flag: yes/no)

---

## ✅ Step 4: Label Aggregation

Link your features (per day or per plot) to the correct label:

| Date       | PlotID | Thrips | Blight | Blotch | Anthracnose |
|------------|--------|--------|--------|--------|-------------|
| 2023-10-01 | R1T1   | 1      | 0      | 0      | 0           |

> 🎯 Use **multi-class** if only one stressor is dominant, or **multi-label** if multiple can appear simultaneously.

---

## ✅ Step 5: Build Classification Model

- Combine all block-wise features into a **single row per sample** (date/plot).
- Use `RandomForestClassifier` or `XGBoost` for initial trials.
- Evaluate feature importance using `.feature_importances_` or SHAP values.

---

## ✅ Step 6: (Optional) Add Lag Features

Fungal diseases often respond to weather from **previous 1–3 days**.

Add these features:
- Mean RH over the last 2 days
- Total rainfall in the last 48 hours
- Max temperature of the previous day

---

## ✅ Sample Feature Output Per Row

| Date       | MeanTemp_8_10 | RH_4_8 | Rain_4_8 | Rain_yesterday | Thrips | Blight | ... |
|------------|---------------|--------|----------|----------------|--------|--------|-----|
| 2023-10-01 | 32.5          | 92%    | 1.2 mm   | 5 mm           | 1      | 0      | ... |

---

Let me know if you'd like help generating the code to automate this feature extraction from your 15-min weather CSV.
