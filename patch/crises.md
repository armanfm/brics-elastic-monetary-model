## 8. Stress Tests of the Elastic Clearing Architecture

### 8. Stress Testing Under Systemic Crises

To evaluate the robustness of the proposed elastic clearing architecture, two historical crisis scenarios were simulated:

- **The 2008 Global Financial Crisis**, characterized primarily by financial system collapse and credit contraction.
- **The COVID-19 pandemic shock**, characterized by a sudden collapse in real economic activity and transaction volume.

These two crises represent fundamentally different types of systemic stress.  
While the 2008 crisis originated in financial markets, the COVID shock primarily affected production, logistics, and transaction flows.

Because the proposed architecture links monetary supply to clearing activity rather than financial market signals, the system reacts differently from traditional fiat monetary regimes.

---

## 8.1 Financial Crisis Scenario (2008-Style Shock)

The 2008 crisis originated in financial leverage and credit system fragility.  
Traditional monetary systems responded through large-scale liquidity injections and balance sheet expansion.

However, the proposed clearing-based architecture is structurally less sensitive to purely financial shocks because the supply mechanism is anchored to **real economic clearing activity rather than financial asset pricing**.

In the simulation, a severe financial shock was introduced to the capital index while keeping transaction activity relatively stable.

The system demonstrated **bounded deviations from its macroeconomic fundamental** and rapid reconvergence due to the elastic adjustment rule:

\[
0 < \alpha k \Delta t < 2
\]

This stability condition ensures that price dynamics remain dampened and prevents runaway oscillations.

The results indicate that financial crises which do not directly disrupt clearing activity have **limited impact on the system's equilibrium**.

---

### Figure 5 — Elastic Reconvergence During a 2008-Style Financial Shock

<img width="1200" height="600" alt="image" src="https://github.com/user-attachments/assets/77e3ed9f-54c4-4d24-8b32-92fb8acf454c" />


Simulation comparing the elastic architecture with a standard GBM benchmark under a financial crisis shock.

---

## 8.2 Real Activity Shock (COVID-19 Scenario)

The COVID-19 pandemic produced a different type of macroeconomic disturbance.

Rather than a financial collapse, it caused a sudden drop in:

- industrial production  
- international trade  
- transaction volume  
- supply chain activity  

In traditional fiat systems, policy responses involved large monetary stimulus packages and aggressive supply expansion.

This often created a temporary mismatch between monetary supply and real production, contributing to inflationary pressures during the recovery phase.

The clearing-based architecture behaves differently.

Because supply is dynamically linked to clearing activity, a decline in transaction volume automatically produces a contraction in monetary supply.

Formally, supply updates follow the clearing growth signal:

\[
g_{clear} = \log\left(\frac{V_t}{V_{t-1}}\right)
\]

which is smoothed through an **exponential moving average** before influencing supply adjustments.

When transaction activity collapses during a lockdown shock:

\[
V_t \downarrow
\]

the resulting signal produces:

\[
Supply \downarrow
\]

This endogenous contraction stabilizes the ratio between monetary supply and real economic activity.

As a result, the purchasing power of the currency remains significantly more stable compared to fiat systems experiencing aggressive stimulus expansion.

---

### Figure 6 — Purchasing Power Dynamics During a COVID-19 Lockdown Shock



Comparison between fiat stimulus dynamics and elastic clearing architecture under transaction collapse.

---

## 8.3 Supply Adjustment Mechanism During Production Collapse

The lower panel of the simulation illustrates the relationship between:

- real economic production  
- fiat monetary expansion  
- elastic supply adjustment  

During the COVID shock:

- **Production experienced a sharp contraction**, while fiat supply expanded due to stimulus measures.
- In contrast, the **elastic clearing architecture reduced supply** in response to declining transaction activity.

This produced a stabilizing effect on the ratio between **money supply and real economic output**.

Consequently, the architecture demonstrates a form of **automatic countercyclical monetary adjustment**, without requiring discretionary intervention by a central authority.

---

### Figure 7 — Supply Adjustment Under Production Collapse

<img width="1000" height="400" alt="Figure" src="https://github.com/user-attachments/assets/df714dad-9a73-43e1-ae47-02657ae4b3fc" />


Comparison between fiat stimulus expansion and elastic supply contraction.

---

## 8.4 Interpretation

These stress tests suggest that the proposed architecture exhibits **structural resilience under both financial and real-activity shocks**.

Financial crises that primarily affect asset markets have limited systemic impact because the supply rule is anchored to **clearing flows rather than speculative valuation**.

Real-activity shocks such as the COVID pandemic do produce temporary contractions in supply, but this contraction acts as a **stabilizing force** that preserves purchasing power and prevents inflationary overshoot during the recovery phase.

The architecture therefore behaves as a **transaction-anchored monetary system**, where monetary supply dynamically adapts to the level of economic activity.

---

## Figure Placement

Use this numbering in the paper:

<img width="1000" height="400" alt="b" src="https://github.com/user-attachments/assets/f289ad0a-eed9-4579-8fb4-01eb38f7b8d0" />
<img width="1000" height="400" alt="c" src="https://github.com/user-attachments/assets/24fd3b66-7c18-4d66-80cd-5a33d88e9cab" />
<img width="1000" height="400" alt="d" src="https://github.com/user-attachments/assets/5693c5a3-434d-483f-90bf-9a903885c660" />

- **Figure 6 — Purchasing Power Dynamics During a COVID-19 Lockdown Shock**
- **Figure 7 — Supply Adjustment Under Production Collapse**
