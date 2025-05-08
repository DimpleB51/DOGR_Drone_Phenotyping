 ###✅Top Vegetation Indices for 5-Band Multispectral Imagery (R, G, B, RE, NIR)**

| **Index**                             | **Formula**                                         | **Sensitivity**                                  | **Best For**                                      |
|--------------------------------------|-----------------------------------------------------|--------------------------------------------------|---------------------------------------------------|
| **NDVI**                              | (NIR - R) / (NIR + R)                               | Chlorophyll content, canopy vigor                | All four diseases                                 |
| **NDRE**                              | (NIR - RE) / (NIR + RE)                             | Early stress detection, especially sub-canopy    | Stemphylium blight, Anthracnose, Purple blotch   |
| **GNDVI**                             | (NIR - G) / (NIR + G)                               | Chlorophyll concentration, pre-symptomatic stress| Anthracnose, Purple blotch                        |
| **Red Edge Chlorophyll Index (CI-RE)**| (NIR / RE) - 1                                      | Leaf chlorophyll changes                         | Anthracnose, Blight                               |
| **Visible Atmospherically Resistant Index (VARI)** | (G - R) / (G + R - B)                     | Detects greenness from RGB only                  | Thrips, general greenness                         |
| **Enhanced Vegetation Index 2 (EVI2)**| 2.5 × (NIR - R) / (NIR + 2.4 × R + 1)                | Improved sensitivity in dense vegetation         | Stemphylium, Purple blotch                        |

 ###🌿 How Each Index Helps
1. NDVI
- Good baseline for disease stress monitoring.
- Disease lesions and Thrips feeding reduce chlorophyll → lower NDVI.

2. NDRE
- Detects stress before symptoms become visible.
- Sensitive to early pathogen activity in lower canopy.

3. GNDVI
- Responds to subtle chlorophyll degradation.
- Better than NDVI for dense onion canopies.

4. CI-RE
- Uses Red Edge, ideal for chlorosis caused by fungal infection.
- Stemphylium blight and Anthracnose lead to high variation in chlorophyll.

5. VARI
- Helpful when using just RGB bands.
- Thrips, which cause silvering and green loss, are captured well here.

6. EVI2
- Reduces background noise, useful in dense fields or mixed vegetation areas.
- Tracks stress severity progression over time.

### 🌿 **Vegetation Indices and Their Applications**

| **Vegetation Index** | **Formula** | **Application in Disease Detection** |
|----------------------|-------------|--------------------------------------|
| **NDVI** (Normalized Difference Vegetation Index) | (NIR - Red) / (NIR + Red) | General indicator of plant health; useful for detecting overall stress caused by diseases like Stemphylium blight and Anthracnose. |
| **GNDVI** (Green Normalized Difference Vegetation Index) | (NIR - Green) / (NIR + Green) | More sensitive to chlorophyll concentration; effective in early detection of diseases such as Purple blotch. |
| **NDRE** (Normalized Difference Red Edge Index) | (NIR - Red Edge) / (NIR + Red Edge) | Detects subtle changes in chlorophyll content; useful for identifying early stress symptoms before they become visible. |
| **MCARI** (Modified Chlorophyll Absorption in Reflectance Index) | [(R700 - R670) - 0.2*(R700 - R550)] * (R700 / R670) | Targets chlorophyll degradation; effective for detecting fungal diseases. |
| **VARI** (Visible Atmospherically Resistant Index) | (Green - Red) / (Green + Red - Blue) | Detects greenness from RGB only; useful for identifying Thrips infestation and general greenness. |

#### Papers to look at 
1. Detection of Twister Disease in Onion Using Sentinel-2 Imagery
2. Onion Crop Monitoring with Multispectral Imagery Using Deep Neural Network
