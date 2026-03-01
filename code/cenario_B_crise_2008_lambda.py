import numpy as np
import matplotlib.pyplot as plt

# =============================
# CONFIG
# =============================

dias = 252 * 5
simulacoes = 200
shock_day = dias // 2

alpha = 0.5
k = 2.0
lambda_fator = 0.75

mu_cap = 0.04
sigma_cap_base = 0.12
sigma_spec_base = 0.01

shock_drop = 0.40
vol_spike_multiplier = 2
vol_spike_days = 60


(aqui voce escolhe o choque externo)
shock_subset = ["BR","RU", "ZA", "EG", "IR"]

# =============================
# DADOS BRICS
# =============================

pib = {
    "CH": 18.0, "IN": 3.7, "RU": 2.2, "BR": 2.1,
    "ZA": 0.4, "EG": 0.4, "ET": 0.15, "IR": 0.6,
    "SAU": 1.1, "UAE": 0.5
}

capital_base = {p: pib[p] * 3.0 for p in pib}
supply = sum(capital_base.values()) / 2.0

# =============================
# PESOS λ
# =============================

def pesos_lambda(pib_dict, lam):
    base = {p: pib_dict[p] ** lam for p in pib_dict}
    s = sum(base.values())
    return {p: base[p] / s for p in base}

w = pesos_lambda(pib, lambda_fator)
hhi = sum(v**2 for v in w.values())

# =============================
# MÉTRICAS
# =============================

def annual_vol(series):
    r = np.diff(np.log(series))
    return np.std(r) * np.sqrt(252)

def max_dd(series):
    peak = np.maximum.accumulate(series)
    return np.min((series - peak) / peak)

def recovery_time(series, shock_idx):
    peak_pre = np.max(series[:shock_idx])
    for i in range(shock_idx, len(series)):
        if series[i] >= peak_pre:
            return i - shock_idx
    return np.nan

def reanchor_time(price, fund, band=0.05):
    err = np.abs(price - fund) / fund
    for i in range(len(err)):
        if err[i] <= band:
            return i
    return np.nan

# =============================
# MONTE CARLO
# =============================

elastic_res = []
gbm_res = []

for sim in range(simulacoes):

    rng = np.random.default_rng(sim)

    capital = capital_base.copy()
    P_elastic = 1.0
    P_gbm = 1.0

    path_el = []
    path_gbm = []
    fund_path = []

    for t in range(dias):

        sigma_cap = sigma_cap_base
        sigma_spec = sigma_spec_base

        # Choque 40%
        if t == shock_day:
            for pais in shock_subset:
                capital[pais] *= (1 - shock_drop)

        # Spike volatilidade 60 dias
        if shock_day <= t < shock_day + vol_spike_days:
            sigma_cap *= vol_spike_multiplier
            sigma_spec *= vol_spike_multiplier

        # Evolução capital por país
        for pais in capital:
            capital[pais] *= np.exp(
                rng.normal(mu_cap/252, sigma_cap/np.sqrt(252))
            )

        # Fundamental ponderado
        C_eff = sum(w[p] * capital[p] for p in capital)
        P_fund = C_eff / supply

        # Elastic
        eps = rng.normal(0, sigma_spec)
        P_spec = P_elastic * np.exp(eps)

        P_adj = P_spec * (P_fund / P_spec) ** k
        P_elastic = (1 - alpha) * P_spec + alpha * P_adj

        # GBM Macro
        P_gbm *= np.exp(
            rng.normal(mu_cap/252, sigma_cap/np.sqrt(252))
        )

        path_el.append(P_elastic)
        path_gbm.append(P_gbm)
        fund_path.append(P_fund)

    path_el = np.array(path_el)
    path_gbm = np.array(path_gbm)
    fund_path = np.array(fund_path)

    elastic_res.append([
        annual_vol(path_el),
        max_dd(path_el),
        recovery_time(path_el, shock_day),
        reanchor_time(path_el[shock_day:], fund_path[shock_day:])
    ])

    gbm_res.append([
        annual_vol(path_gbm),
        max_dd(path_gbm),
        recovery_time(path_gbm, shock_day)
    ])

elastic_res = np.array(elastic_res)
gbm_res = np.array(gbm_res)

print("\n===== CENÁRIO B – CRISE 2008-STYLE =====")
print(f"lambda: {lambda_fator} | HHI: {round(hhi,3)}")

print("\nElastic:")
print("Vol:", np.mean(elastic_res[:,0]))
print("MDD:", np.mean(elastic_res[:,1]))
print("Rec. Pico (dias):", np.nanmean(elastic_res[:,2]))
print("Reanchor (dias):", np.nanmean(elastic_res[:,3]))

print("\nGBM Macro:")
print("Vol:", np.mean(gbm_res[:,0]))
print("MDD:", np.mean(gbm_res[:,1]))
print("Rec. Pico (dias):", np.nanmean(gbm_res[:,2]))

# =============================
# FIGURA EXEMPLO
# =============================

plt.figure(figsize=(8,5))
plt.plot(path_el, label="Elastic")
plt.plot(path_gbm, label="GBM Macro")
plt.plot(fund_path, linestyle="--", label="Fundamental")
plt.axvline(shock_day, linestyle=":")
plt.title("Cenário B – 2008-style (40% + Spike 2x)")
plt.legend()
plt.tight_layout()

plt.savefig("cenario_B_2008_lambda.png", dpi=300, bbox_inches="tight")
plt.savefig("cenario_B_2008_lambda.pdf", bbox_inches="tight")

plt.show()
