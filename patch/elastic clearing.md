# Single-Country Clearing Monetary Model — Crisis Simulations

## Overview

This section documents stress tests performed on the **elastic clearing-based monetary model** applied to a single-country economy.

The goal is to evaluate how a monetary system whose supply follows **domestic economic activity** behaves under severe macroeconomic crises historically observed in emerging economies.

Two crisis types were simulated:

- **Argentina-style inflationary crisis**
- **Venezuela-style hyperinflation**

The simulations compare:

**Traditional FIAT monetary regime**  
vs  
**Elastic Clearing Monetary Regime**

---

# Test 1 — Argentina-Style Inflation Crisis

## Real-world reference

Argentina has experienced repeated inflation crises.  
Annual inflation exceeded **200% in 2023**, one of the highest levels in the world. :contentReference[oaicite:0]{index=0}

These crises typically involve:

- currency depreciation  
- government monetary expansion  
- persistent inflation expectations  

## Simulation Design

The simulation introduces:

- exchange rate depreciation  
- monetary expansion  
- moderate production decline  

These conditions represent a typical **inflationary environment in emerging economies**.

## Simulation Result

Observed output from the model:


Maximum inflation (FIAT): 17.75 %
Maximum inflation (Clearing): 0.47 %


## Interpretation

In the **fiat regime**:

monetary supply expands independently of production.

This allows price levels to rise rapidly.

In the **clearing regime**:

money supply adjusts toward **domestic economic activity**,  
which stabilizes the price level.

---

# Test 2 — Venezuela-Style Hyperinflation

## Real-world reference

Venezuela experienced one of the worst hyperinflations in modern history.

Inflation reached extremely high levels, including:

- **130,060% in 2018**
- **9,586% in 2019**

according to central bank data. :contentReference[oaicite:1]{index=1}

## Simulation Design

The test introduces a hyperinflationary environment:

- extreme currency depreciation  
- aggressive monetary expansion  
- declining production  

These factors historically triggered **runaway inflation**.

## Simulation Result

Example simulation output:


Maximum inflation (FIAT): 3157.79 %
Maximum inflation (Clearing): 0.41 %


## Interpretation

In the **fiat system**:

money supply expands without structural constraint,  
which produces **runaway inflation**.

In the **clearing model**:

supply remains **anchored to production**,  
creating an **automatic stabilization mechanism**.

---

# Structural Observation

Across both experiments, the system exhibits a **feedback stabilization behavior**:


price deviation
→ elastic correction
→ reconvergence toward fundamental


The reconvergence parameter **K** functions similarly to a **gain parameter in control systems**, determining the strength of the correction force.

---

# Key Observation from the Experiments

In both crisis simulations:

- **FIAT systems produced large inflation shocks**
- **Clearing systems maintained near-stable prices**

The stabilizing mechanism arises from:


production / supply anchoring
+
elastic reconvergence


---

# Model Assumptions

The simulations rely on simplified assumptions:

- production proxy used for economic activity  
- simplified behavioral responses  
- no political intervention  
- no banking sector dynamics  

These assumptions isolate the **structural behavior of the monetary rule**.

---

# Conclusion

The experiments suggest that a **clearing-based elastic monetary system applied to a single-country economy** can demonstrate strong stability properties even under severe crisis conditions.

Tested scenarios include:

- inflationary currency crisis  
- hyperinflation environment  

In both cases, the simulations indicate that the clearing-based rule maintains:

- **bounded inflation**
- **stable price dynamics**
- **reconvergence toward macroeconomic fundamentals**

Further empirical testing using **real macroeconomic datasets** would be necessary to evaluate real-world feasibility.
