
# Stress Scenario 3 — External Currency Shock

## Objective

Simulate a scenario where:

external exchange rate collapses.

This models crises similar to:

- emerging market currency crashes  
- import-driven inflation  

Two systems were compared:

- **Traditional FIAT monetary regime**
- **Elastic clearing monetary system**

## Simulation Result

Example output:


Maximum inflation (FIAT): 17.75%
Maximum inflation (Clearing): 0.47%


The clearing system shows **strong resistance to external currency shocks** because:

- supply follows **domestic activity**
- rather than **external currency valuation**

## Figure

*(Insert graph here)*

![Currency Crisis](images/currency_crisis.png)

---

# Stress Scenario 4 — Hyperinflation Dynamics  
*(Argentina / Venezuela Style)*

This test introduces:

- currency depreciation  
- monetary expansion  
- production decline  

Typical of **hyperinflationary episodes**.

## Simulation Output Example


Maximum inflation (FIAT): 3157.79 %
Maximum inflation (Clearing): 0.41 %


This difference arises because:

**FIAT systems allow:**

supply expansion disconnected from production.

While the clearing model enforces:

production / supply anchoring.

## Figure

*(Insert graph here)*

![Hyperinflation Scenario](images/hyperinflation.png)

---

# Structural Observation

Across all simulations, the system behaves like a **feedback-stabilized dynamic system**:

price deviation → elastic correction → reconvergence

This structure is mathematically similar to **control-system feedback stabilization**.

The parameter **K** functions analogously to a **gain parameter controlling the strength of the correction force**.

---

# Limitations

These simulations assume simplified economic conditions:

- rational agent behavior  
- simplified production proxy  
- no political intervention  
- simplified capital dynamics  

Real-world implementation would require **additional institutional mechanisms**.

---

# Conclusion

The computational experiments suggest that a **clearing-anchored elastic monetary architecture** can exhibit **strong stability properties** under multiple crisis conditions, including:

- financial shocks  
- transaction collapse  
- currency crises  
- hyperinflation scenarios  

Further empirical testing using **real economic data** would be required to evaluate **practical feasibility**.

---

# Possible Extension for Academic Publication

A potential extension for a research paper would be a section titled:

## Dynamic Stability Proof of the Elastic Reconvergence Mechanism

This section would provide a **formal mathematical demonstration** that the elastic reconvergence rule ensures **bounded convergence toward the macroeconomic fundamental**, rather than relying solely on simulation results.

Such analytical proof strengthens the theoretical foundations of the model and is often valued by academic reviewers.
