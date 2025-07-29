# weather_master_sheet generates weather master excel sheet
2 files are required to generate this code **Jan-Sept_2024_Weather_data.xlsx** and **weather.csv** these are the excel sheets from the weather station
### CODE to generate weather data in blocks (Trial_wise)
Blocks are <br/>
- B1 (4-8am) <br/>
- B2 (8-10am) <br/>
- B3 (10-12pm) <br/>
- B4 (12-2pm) <br/>
- B5 (2-4pm) <br/>

```
1_weather_data_blocks.ipynb
```

generates file **weather_master_data.xlsx**


### CODE to generate weather data by taking average in the day
NOTE: Blocks arn't considered only average is taken across the days <br/>

```
weather_data.ipynb
```

generates file **weather_master_dayval.xlsx** <br/>

### CODE to generate aggregated weather data

```
weather_data_trialscomb.ipynb
```
generates file **aggregated_weather_data.xlsx** <br/>

Note: 1 excel sheet is generated with all dates and their respective weather parameters

# EDA

### All time blocks and the relevant feature
In the file <br/>
```
EDA_weather.ipynb
```
plots are displayed for all time blocks and grouping is done here. <br/>

The another file <br/>
```
EDA_weather-Correlation.ipynb
```
displays pearson correlation between weather parameters and diseases.

###  Weather correlation for average parameters in a day
To only look at the average parameters in a day, **not** looking at time blocks.<br/>
Use the script <br/>
```
EDA_weather_noblocks.ipynb
```
plots are displayed for all parameters. <br/>

The another file <br/>
```
EDA_weather-Correlation-noblocks.ipynb
```
displays pearson correlation between weather parameters and diseases.

# Just looking at rainfall
```
EDA_weather_noblocks-rain.ipynb
```
plots just rainfall weather_data <br/>

##### 2 files displays
```
EDA_weather-Correlation-rainfall-alltrials.ipynb
```
pearson correlation analysis for all trials

```
EDA_weather-Correlation-rainfall-4trials.ipynb
```
person correlation analysis for only 4 trials when rainfall is present
