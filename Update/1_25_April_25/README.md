# EDA Analysis
Single variate analysis done for Region R3T3
![img](./EDA_Analysis/EDA_R1.png)

### Table indices calculation
| **Index** | **Formula** | **Best For** | **Sensitivity** | **Growth Stage Suitability** | **Notes on Onion Suitability** |
|----------|-------------|--------------|------------------|------------------------------|--------------------------------|
| **NDVI** | (NIR - Red)/(NIR + Red) | General biomass, vigor | Saturates in dense canopy | Early to mid-stage | May saturate in late stages; useful for early vigor detection |
| **GNDVI** | (NIR - Green)/(NIR + Green) | Chlorophyll/nitrogen status | More sensitive than NDVI | Mid to late | More responsive to nitrogen changes; good for assessing green-leaf density |
| **NDRE** | (NIR - RedEdge)/(NIR + RedEdge) | Chlorophyll, nitrogen, late-stage crops | High (deep canopy) | Mid to late | Very effective for late-stage onions and nutrient stress detection |
| **LAI** | Empirical (e.g. from EVI) | Leaf area, yield modeling | High (biophysical) | All stages (calibration needed) | Good for modeling growth, but needs calibration; may underestimate due to onion’s narrow leaves |
| **NORM2** | (Red - Green)/(Red + Green) or L2 norm of bands | General vegetation detection | Low to moderate | Early detection | Fast, simple; works when NIR is unavailable (e.g. RGB UAVs) |
