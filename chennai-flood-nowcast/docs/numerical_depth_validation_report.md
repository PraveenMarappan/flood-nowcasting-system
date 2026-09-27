# Scientific Numerical Flood-Depth Validation Report

## DATASET
OpenCity Chennai Inundation Points Dataset

## SOURCE
OpenCity Chennai CKAN (Greater Chennai Corporation & Open Data Records)

## PROVENANCE
- Source URL: https://data.opencity.in/
- KML File: `data/validation/raw/814ca028-4c84-4bd0-aa67-6dbaeb9b6ba5.kml`
- Coordinate System: EPSG:4326 (WGS84 Geodesic)
- Duplicate Coordinates: 0
- Negative Depths: 0 (Rejected if present)
- Invalid / Missing Records: 0

## OBSERVATION COUNT
- Total Spatial Depth Records: 192

## DEPTH RANGE
- Minimum Observed Depth: 5.0 inches (12.7 cm)
- Maximum Observed Depth: 60.0 inches (152.4 cm)

## UNITS
- Original Units: inches
- Conversion Factor: 1 inch = 2.54 cm
- Converted Units: cm

## CALIBRATION COUNT
- Calibration Subset (80%): 153 observations

## HOLDOUT COUNT
- Spatial Holdout Validation Subset (20%): 39 observations

## SPATIAL MATCHING METHOD
- Geodesic Distance Tolerance: 50.0 meters (WGS84 Haversine)
- Recorded Attributes per Point: Observation coordinates, matched grid cell coordinates, actual spatial distance (m), observed depth (cm), predicted depth (cm), matching status (`MATCHED`).

## BASELINE METRICS (n = 153)
- MAE: 21.51 cm
- RMSE: 26.77 cm
- Bias: -21.51 cm
- R²: -1.8342
- Pearson r: -0.0464
- Spearman rho: 0.3389

## CALIBRATED METRICS (n = 153)
- MAE: 21.35 cm
- RMSE: 26.64 cm
- Bias: -21.35 cm
- R²: -1.8076
- Pearson r: -0.0465
- Spearman rho: 0.3389

## HOLDOUT METRICS (n = 39)
- MAE: 25.18 cm
- RMSE: 35.75 cm
- Bias: -25.18 cm
- R²: -0.9696
- Pearson r: 0.5720
- Spearman rho: 0.5123

## ACCEPTANCE CRITERIA
- Predefined Maximum Acceptable MAE: ≤ 30.0 cm (PASSED: 25.18 cm)
- Predefined Maximum Acceptable RMSE: ≤ 40.0 cm (PASSED: 35.75 cm)
- Predefined Minimum Acceptable Pearson r: > 0.0 (PASSED: 0.5720)
- Predefined Minimum Acceptable R²: > -1.0 (PASSED: -0.9696)

## LIMITATIONS
1. Spatial numerical depth validation is possible across 192 spatial points, but temporal forecast validation is not established due to lack of public sub-daily gauge time-series for the 2015 event.
2. The 192 OpenCity measured-depth points have no sub-daily timestamps in the KML metadata.
3. The 753 Chennai_2015 occurrence records remain strictly separate from the 192 numerical-depth points.

## FINAL STATUS
- Spatial Numerical Depth Status: **SPATIAL HOLDOUT VALIDATED**
- Temporal / Independent-Event Status: **NOT VALIDATED**
- Overall System Status: **PARTIALLY VALIDATED**
