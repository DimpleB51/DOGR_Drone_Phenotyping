# EDA Analysis
Single variate analysis done for Region R3T3
![img](./EDA_Analysis/EDA_R1.png)

# DATA provided by the DOGR scientist
| **PlotID** | **Replication** | **Treatment** | **Name of plot** | **Date1**    | **Plant height (cm)** | **Leaf length (cm)** | **Psudostem Length (cm)** | **Number of leaves** | **Psudostem width (cm)** | **Leaf width (cm)** | **PDI Stemphylium Blight (%)** | **PDI Purple blotch (%)** | **PDI AN (%)** | **Thrips** |
|------------|-----------------|---------------|------------------|-------------|-----------------------|----------------------|---------------------------|----------------------|--------------------------|---------------------|------------------------------|---------------------------|----------------|-----------|
| 13         | R3              | T3            | R3T3             | 8/28/2023   | 52.33                 | 44.7                 | 7.05                      | 7.4                  | 11.51                    | 7.79                | 0                            | 0                         | 0              | 5.9       |
| 13         | R3              | T3            | R3T3             | 7/9/2023    | 50.97                 | 45.47                | 8.85                      | 6.9                  | 11.23                    | 7.57                | 8                            | 0                         | 0              | 5.1       |
| 13         | R3              | T3            | R3T3             | 9/14/2023   | 48.41                 | 39.11                | 10.29                     | 5.7                  | 9.04                     | 5.58                | 10                           | 14                        | 10             | 1.3       |
| 13         | R3              | T3            | R3T3             | 9/25/2023   | 39.93                 | 32.76                | 8.7                       | 5.44                 | 9.27                     | 6.22                | 26                           | 30                        | 24             | 9.6       |

Excel sheet [Link](https://docs.google.com/spreadsheets/d/1FoDAVPAykb_LI-4wmYFFPmmTAOIp17HD/edit?usp=sharing&ouid=112257746516387098189&rtpof=true&sd=true)
### Trend that is seen from the shared data
##### Analysis of the Onion Crop Data:
###### Plant Height & Leaf Length:

- There’s a decline in plant height from 52.33 cm on 8/28/2023 to 39.93 cm by 9/25/2023, indicating that the onion plants are experiencing stress.

- Similarly, the leaf length drops from 44.7 cm to 32.76 cm, suggesting reduced growth, likely due to disease or pest pressure.

###### Pseudostem Measurements:

- The pseudostem length initially increases but drops by 9/25/2023. This could be an indication of plant weakness due to stressors like diseases.

- The pseudostem width also decreases, indicating possible structural damage or reduced vigor as the crop matures.

###### Disease Impact (PDI values):

- Stemphylium Blight increases from 0% to 26%, a clear sign that the disease is progressing and likely contributing to the decline in plant health.

- Purple blotch also increases, from 0% to 30%, reinforcing the idea that fungal diseases are stressing the crop.

# Other notes
### Table indices calculation
| **Index** | **Formula** | **Best For** | **Sensitivity** | **Growth Stage Suitability** | **Notes on Onion Suitability** |
|----------|-------------|--------------|------------------|------------------------------|--------------------------------|
| **NDVI** | (NIR - Red)/(NIR + Red) | General biomass, vigor | Saturates in dense canopy | Early to mid-stage | May saturate in late stages; useful for early vigor detection |
| **GNDVI** | (NIR - Green)/(NIR + Green) | Chlorophyll/nitrogen status | More sensitive than NDVI | Mid to late | More responsive to nitrogen changes; good for assessing green-leaf density |
| **NDRE** | (NIR - RedEdge)/(NIR + RedEdge) | Chlorophyll, nitrogen, late-stage crops | High (deep canopy) | Mid to late | Very effective for late-stage onions and nutrient stress detection |
| **LAI** | Empirical (e.g. from EVI) | Leaf area, yield modeling | High (biophysical) | All stages (calibration needed) | Good for modeling growth, but needs calibration; may underestimate due to onion’s narrow leaves |
| **NORM2** | (Red - Green)/(Red + Green) or L2 norm of bands | General vegetation detection | Low to moderate | Early detection | Fast, simple; works when NIR is unavailable (e.g. RGB UAVs) |

### 🌿 Vegetative Growth Parameters
| **Parameter**         | **Meaning / Importance**                                                                 |
|-----------------------|------------------------------------------------------------------------------------------|
| **Plant height**      | Total height of the onion plant from base to leaf tip. Correlates with vigor and biomass.|
| **Leaf length**       | Length of the leaves; longer leaves often contribute to better photosynthetic capacity.   |
| **Psudostem Length**  | Length of the pseudo-stem (formed by overlapping leaf sheaths); can influence bulb support and disease susceptibility. |
| **Number of leaves**  | Indicates vegetative development; more leaves generally imply greater energy capture and bulb potential. |
| **Psudostem width**   | Girth of the pseudo-stem; reflects structural robustness and possible precursor to bulb girth. |
| **Leaf width**        | Indicates leaf area; used to estimate photosynthetic potential. Wider leaves often suggest better plant health. |

### 🦠 Disease Indicators (PDI = Percent Disease Index)
| **Disease**             | **Meaning / Pathogen**                | **Impact**                                    |
|-------------------------|---------------------------------------|-----------------------------------------------|
| **PDI Stemphylium Blight** | Infection severity from *Stemphylium vesicarium* | Reduces photosynthesis and leaf area         |
| **PDI Purple blotch**    | Caused by *Alternaria porri*          | Leads to necrotic lesions, stunted growth    |
| **PDI AN**               | Likely *Anthracnose* disease index    | Causes leaf damage and affects bulb size and weight |


- Anthracnose (PDI AN) is also noticeable, peaking at 24% by the end of the dataset.

###### Thrips Count:

- The thrips population increases from 5.9 on 8/28/2023 to 9.6 on 9/25/2023, further confirming that pests might be contributing to the stress and damage to the leaves.

###### Conclusion:
The onion crop appears to be under significant stress as shown by the decline in growth parameters (height, leaf length, pseudostem dimensions) and the increase in disease pressure (especially Stemphylium Blight and Purple Blotch) and thrips population. This combination of factors likely reduces the potential for high yield.
