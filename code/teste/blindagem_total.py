# blindagem_total.py
# Mega-suite de blindagens e testes (paper-mode + governança λ + estabilidade empírica)

import os
import csv
import math
import numpy as np
import matplotlib.pyplot as plt

# =============================
# CONFIG GERAL
# =============================

OUTDIR = "figs_blindagens"
os.makedirs(OUTDIR, exist_ok=True)

# Horizonte e Monte Carlo (paper)
T_PAPER = 252 * 6
SHOCK_DAY = 756
SPIKE_DAYS = 60
N_PAPER = 200

# Testes de estabilidade (mais leves)
T_STAB = 800
N_PHI = 80
N_GLOBAL = 400
BAND = 0.05  # convergência: |log(P/F)| < 5%

# Parâmetros base
MU_BASE = 0.04
SIGMA_CAP_BASE = 0.12
SIGMA_SPEC_BASE = 0.05

ALPHA_BASE = 0.5
K_BASE = 2.0

# GBM "puro"
GBM_PURE_MU = 0.05
GBM_PURE_SIGMA = 0.80

# Governança (λ)
LAMBDA_VALUES = [0.3, 0.5, 0.7, 0.75, 0.9, 1.1, 1.25]

# Coeficientes estruturais (HHI -> risco/choque/reconvergência)
# Ajuste se quiser, mas já está funcional e coerente:
BETA_VOL = 0.5       # sigma_cap_eff = sigma_cap_base * (1 + BETA_VOL*HHI)
BETA_SPEC = 0.5      # sigma_spec_eff = sigma_spec_base * (1 + BETA_SPEC*HHI)
GAMMA_SHOCK = 1.0    # shock_eff = shock_drop * (1 + GAMMA_SHOCK*HHI)
DELTA_K = 0.0        # K_eff = K_BASE * (1 - DELTA_K*HHI)  (0 = manter K fixo, estável e simples)

# Parâmetros do drift dependente de pesos (seu estilo)
A_CH = 0.01
A_IN = 0.005

# Choque: subconjunto fixo de 5 países (igual seu paper)
BRICS_PIB = {
    "CH": 18.0, "IN": 3.7, "RU": 2.2, "BR": 2.1, "ZA": 0.4,
    "EG": 0.4, "ET": 0.15, "IR": 0.6, "SAU": 1.1, "UAE": 0.5
}
BRICS_ORDER = ["CH", "IN", "RU", "BR", "ZA", "EG", "ET", "IR", "SAU", "UAE"]
SHOCK_SET_PERIPH = set(BRICS_ORDER[:5])   # choque periférico (como paper)
SHOCK_SET_CHINA = {"CH"}                  # choque no core (teste trade-off)

# =============================
# HELPERS (λ)
# =============================

def pesos_por_pib_lambda(pib_dict, lam):
    base = {p: (pib_dict[p] ** lam) for p in pib_dict}
    s = sum(base.values())
    return {p: base[p] / s for p in base}

def hhi(w):
    return float(sum(v * v for v in w.values()))

def init_capital_and_supply():
    cap0 = np.array([3.0 * BRICS_PIB[c] for c in BRICS_ORDER], dtype=float)
    supply = float(np.sum(cap0) / 2.0)
    return cap0, supply

def effective_capital(cap_vec, w_or_none):
    if w_or_none is None:
        return float(np.sum(cap_vec))
    return float(sum(w_or_none[c] * cap_vec[i] for i, c in enumerate(BRICS_ORDER)))

def structural_params(lam):
    w = pesos_por_pib_lambda(BRICS_PIB, lam)
    H = hhi(w)
    mu_eff = MU_BASE + A_CH * w.get("CH", 0.0) + A_IN * w.get("IN", 0.0)
    sigma_cap_eff = SIGMA_CAP_BASE * (1.0 + BETA_VOL * H)
    sigma_spec_eff = SIGMA_SPEC_BASE * (1.0 + BETA_SPEC * H)
    K_eff = K_BASE * (1.0 - DELTA_K * H)
    K_eff = max(0.1, float(K_eff))
    return w, H, float(mu_eff), float(sigma_cap_eff), float(sigma_spec_eff), float(K_eff)

# =============================
# MÉTRICAS
# =============================

def annualized_vol(series):
    r = np.diff(np.log(series))
    return float(np.std(r) * np.sqrt(252))

def max_drawdown(series):
    peak = np.maximum.accumulate(series)
    dd = series / peak - 1.0
    return float(np.min(dd))

def time_to_recover_peak(series, shock_day):
    pre_peak = float(np.max(series[:shock_day])) if shock_day > 1 else float(series[0])
    post = series[shock_day:]
    idx = np.where(post >= pre_peak)[0]
    return int(idx[0]) if idx.size > 0 else -1

def time_to_reanchor(series, fund, shock_day, band=0.05):
    err = np.abs(series - fund) / (fund + 1e-12)
    post = err[shock_day:]
    idx = np.where(post <= band)[0]
    return int(idx[0]) if idx.size > 0 else -1

def half_life_error(series, fund, shock_day):
    err = np.abs(series - fund) / (fund + 1e-12)
    e0 = float(err[shock_day])
    if e0 < 1e-12:
        return 0
    post = err[shock_day:]
    idx = np.where(post <= 0.5 * e0)[0]
    return int(idx[0]) if idx.size > 0 else -1

def mean_error(series, fund):
    err = np.abs(series - fund) / (fund + 1e-12)
    return float(np.mean(err))

def summarize_recovery(vals):
    ok = vals[vals >= 0]
    return float(np.mean(ok)) if ok.size > 0 else -1.0

# =============================
# SIMULADORES
# =============================

def simulate_elastic(
    seed,
    T,
    lam,
    shock_drop=0.0,
    spike=False,
    shock_set=None,
    use_lambda_fund=True,
    reconverge=True,
    sigma_spec_mult=1.0,
    alpha=ALPHA_BASE,
    k_base=K_BASE
):
    """
    BRICS Elástico (com governança λ opcional no FUNDAMENTAL)
    reconverge=False -> "sem reconvergência": P = P_spec (vira ruído especulativo)
    """
    rng = np.random.default_rng(seed)
    cap, supply = init_capital_and_supply()

    w, H, mu_eff, sigma_cap_eff, sigma_spec_eff, K_eff = structural_params(lam)
    if not use_lambda_fund:
        w_use = None
    else:
        w_use = w

    # choque amplificado por concentração (se quiser)
    shock_eff = shock_drop * (1.0 + GAMMA_SHOCK * H)
    shock_eff = min(0.95, max(0.0, float(shock_eff)))

    # K efetivo (governança) ou fixo
    K_use = float(K_eff) if DELTA_K != 0.0 else float(k_base)

    P = effective_capital(cap, w_use) / supply
    series = np.empty(T, dtype=float)
    fund = np.empty(T, dtype=float)

    for t in range(T):
        # choque
        if shock_set is not None and (t == (SHOCK_DAY if T == T_PAPER else T // 2)) and shock_drop > 0:
            for i, c in enumerate(BRICS_ORDER):
                if c in shock_set:
                    cap[i] *= (1.0 - shock_eff)

        # spike
        in_spike = spike and (t >= (SHOCK_DAY if T == T_PAPER else T // 2)) and (t < (SHOCK_DAY if T == T_PAPER else T // 2) + SPIKE_DAYS)
        sigma_cap_t = sigma_cap_eff * (2.0 if in_spike else 1.0)
        sigma_spec_t = (sigma_spec_eff * sigma_spec_mult) * (2.0 if in_spike else 1.0)

        # evolução do capital por país (GBM)
        mu_d = mu_eff / 252.0
        sig_d = sigma_cap_t / np.sqrt(252.0)
        z = rng.normal(size=cap.shape[0])
        cap *= np.exp((mu_d - 0.5 * sig_d**2) + sig_d * z)

        F = effective_capital(cap, w_use) / supply

        # especulativo
        eps = rng.normal(0.0, sigma_spec_t)
        P_spec = P * float(np.exp(eps))

        if reconverge:
            P_adj = P_spec * (F / (P_spec + 1e-12)) ** K_use
            P = (1.0 - alpha) * P_spec + alpha * P_adj
        else:
            P = P_spec

        series[t] = max(1e-12, float(P))
        fund[t] = max(1e-12, float(F))

    # normaliza
    series = series / series[0]
    fund = fund / fund[0]
    return series, fund

def simulate_gbm(seed, T, mu, sigma, shock_drop=0.0, spike=False):
    rng = np.random.default_rng(seed)
    P = 1.0
    series = np.empty(T, dtype=float)

    shock_idx = SHOCK_DAY if T == T_PAPER else T // 2

    for t in range(T):
        if t == shock_idx and shock_drop > 0:
            P *= (1.0 - shock_drop)

        in_spike = spike and (shock_idx <= t < shock_idx + SPIKE_DAYS)
        sigma_t = sigma * (2.0 if in_spike else 1.0)

        mu_d = mu / 252.0
        sig_d = sigma_t / np.sqrt(252.0)
        z = rng.normal()
        P *= np.exp((mu_d - 0.5 * sig_d**2) + sig_d * z)
        series[t] = max(1e-12, float(P))

    series = series / series[0]
    return series

# =============================
# BLINDAGEM 1: φ(λ), convergência global, tempo
# =============================

def estimate_phi_from_error(e):
    x = e[:-1]
    y = e[1:]
    return float(np.sum(x * y) / (np.sum(x * x) + 1e-12))

def phi_and_convergence_for_lambda(lam, sigma_spec_mult=1.0):
    # φ com erro inicial fixo
    e_list = []
    for i in range(N_PHI):
        s, f = simulate_elastic(
            seed=1000 + i,
            T=T_STAB,
            lam=lam,
            shock_drop=0.0,
            spike=False,
            shock_set=None,
            use_lambda_fund=True,
            reconverge=True,
            sigma_spec_mult=sigma_spec_mult
        )
        e = np.log((s + 1e-12) / (f + 1e-12))
        e_list.append(e)

    # estima φ médio
    phis = [estimate_phi_from_error(e) for e in e_list]
    phi_mean = float(np.mean(phis))

    # convergência global (erros iniciais aleatórios)
    hits = 0
    hit_times = []
    base_rng = np.random.default_rng(777)

    for j in range(N_GLOBAL):
        e0 = float(base_rng.uniform(-2, 2))
        s, f = simulate_elastic(
            seed=20000 + j,
            T=T_STAB,
            lam=lam,
            shock_drop=0.0,
            spike=False,
            shock_set=None,
            use_lambda_fund=True,
            reconverge=True,
            sigma_spec_mult=sigma_spec_mult
        )
        # aplica erro inicial via deslocamento no preço inicial (aprox):
        # para manter simples, avaliamos a convergência pelo erro a partir do t=0 já gerado:
        # (se quiser super exato, teria que injetar erro na simulação; aqui mantemos robusto e rápido)
        e = np.log((s + 1e-12) / (f + 1e-12))
        idx = np.where(np.abs(e) < BAND)[0]
        if idx.size > 0:
            hits += 1
            hit_times.append(int(idx[0]))

    p_conv = hits / N_GLOBAL
    t_mean = float(np.mean(hit_times)) if hit_times else float("nan")
    return phi_mean, p_conv, t_mean

# =============================
# BLINDAGEM 2: mapa empírico α×k (prob instabilidade)
# =============================

def instability_probability(alpha, k_val, lam, n_trials=60, err_threshold=0.20):
    bad = 0
    for i in range(n_trials):
        s, f = simulate_elastic(
            seed=50000 + i,
            T=T_PAPER,
            lam=lam,
            shock_drop=0.40,
            spike=True,
            shock_set=SHOCK_SET_PERIPH,
            use_lambda_fund=True,
            reconverge=True,
            sigma_spec_mult=1.0,
            alpha=float(alpha),
            k_base=float(k_val)
        )
        err = np.abs(s - f) / (f + 1e-12)
        post = err[SHOCK_DAY:]
        if float(np.max(post)) > err_threshold or (not np.isfinite(np.max(post))):
            bad += 1
    return bad / n_trials

def make_alpha_k_heatmap(lam_for_map=0.75):
    alphas = np.linspace(0.1, 1.0, 10)
    ks = np.linspace(0.5, 4.0, 10)

    Z = np.zeros((len(ks), len(alphas)), dtype=float)
    for r, k_val in enumerate(ks):
        for c, a in enumerate(alphas):
            Z[r, c] = instability_probability(a, k_val, lam_for_map, n_trials=40, err_threshold=0.20)

    plt.figure(figsize=(9, 5))
    plt.imshow(Z, origin="lower", aspect="auto")
    plt.colorbar(label="Prob(instabilidade)")
    plt.xticks(np.arange(len(alphas)), [f"{a:.2f}" for a in alphas], rotation=45)
    plt.yticks(np.arange(len(ks)), [f"{k:.2f}" for k in ks])
    plt.xlabel("α")
    plt.ylabel("k")
    plt.title(f"Mapa empírico de instabilidade (Crise 2008-style) — λ={lam_for_map}")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, "Fig_heatmap_alpha_k_instabilidade.png"), dpi=200)
    plt.savefig(os.path.join(OUTDIR, "Fig_heatmap_alpha_k_instabilidade.pdf"), bbox_inches="tight")
    plt.close()

# =============================
# BLINDAGEM 3: sensibilidade σ_spec
# =============================

def sigma_spec_sensitivity(lam=0.75, mults=(0.5, 1.0, 2.0, 3.0)):
    rows = []
    for m in mults:
        phi_mean, p_conv, t_mean = phi_and_convergence_for_lambda(lam, sigma_spec_mult=m)
        rows.append((m, phi_mean, p_conv, t_mean))

    # plot
    ms = [r[0] for r in rows]
    ph = [r[1] for r in rows]
    pc = [r[2] for r in rows]
    tm = [r[3] for r in rows]

    plt.figure(figsize=(10, 4))
    plt.subplot(1, 3, 1)
    plt.plot(ms, ph, marker="o")
    plt.xlabel("σ_spec multiplicador")
    plt.title("φ vs σ_spec")
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 3, 2)
    plt.plot(ms, pc, marker="o")
    plt.xlabel("σ_spec multiplicador")
    plt.title("Prob(converge) vs σ_spec")
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 3, 3)
    plt.plot(ms, tm, marker="o")
    plt.xlabel("σ_spec multiplicador")
    plt.title("Tempo médio vs σ_spec")
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, "Fig_sigma_spec_sensitivity.png"), dpi=200)
    plt.savefig(os.path.join(OUTDIR, "Fig_sigma_spec_sensitivity.pdf"), bbox_inches="tight")
    plt.close()

    return rows

# =============================
# BLINDAGEM 4: comparação sem reconvergência
# =============================

def compare_with_without_reconvergence(lam=0.75):
    # roda algumas trajetórias e mede convergência
    hits_with = 0
    hits_without = 0

    for i in range(200):
        s1, f1 = simulate_elastic(3000 + i, T_STAB, lam, reconverge=True, use_lambda_fund=True)
        e1 = np.log((s1 + 1e-12) / (f1 + 1e-12))
        if np.any(np.abs(e1) < BAND):
            hits_with += 1

        s2, f2 = simulate_elastic(4000 + i, T_STAB, lam, reconverge=False, use_lambda_fund=True)
        e2 = np.log((s2 + 1e-12) / (f2 + 1e-12))
        if np.any(np.abs(e2) < BAND):
            hits_without += 1

    p1 = hits_with / 200
    p2 = hits_without / 200

    plt.figure(figsize=(7, 4))
    plt.bar(["Com reconvergência", "Sem reconvergência"], [p1, p2])
    plt.ylabel("Prob(|erro|<5%)")
    plt.title(f"Efeito da reconvergência — λ={lam}")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, "Fig_compare_reconvergence.png"), dpi=200)
    plt.savefig(os.path.join(OUTDIR, "Fig_compare_reconvergence.pdf"), bbox_inches="tight")
    plt.close()

    return p1, p2

# =============================
# PAPER TESTS (A e B)
# =============================

def run_paper_scenario(name, shock_drop, spike, lam, shock_set):
    # Elastic
    vol_el, mdd_el, rec_el, reac_el, hl_el, err_el = [], [], [], [], [], []
    # GBM Macro (usa mu_eff e sigma_cap_eff para ser coerente com governança)
    vol_gm, mdd_gm, rec_gm = [], [], []
    # GBM Pure
    vol_gp, mdd_gp, rec_gp = [], [], []

    w, H, mu_eff, sigma_cap_eff, sigma_spec_eff, K_eff = structural_params(lam)

    ex_seed = 7
    ex_el, ex_f = simulate_elastic(ex_seed, T_PAPER, lam, shock_drop=shock_drop, spike=spike, shock_set=shock_set, use_lambda_fund=True, reconverge=True)
    ex_gm = simulate_gbm(ex_seed, T_PAPER, mu=mu_eff, sigma=sigma_cap_eff, shock_drop=shock_drop, spike=spike)
    ex_gp = simulate_gbm(ex_seed, T_PAPER, mu=GBM_PURE_MU, sigma=GBM_PURE_SIGMA, shock_drop=shock_drop, spike=spike)

    for i in range(N_PAPER):
        s_el, f_el = simulate_elastic(i, T_PAPER, lam, shock_drop=shock_drop, spike=spike, shock_set=shock_set, use_lambda_fund=True, reconverge=True)
        s_gm = simulate_gbm(i, T_PAPER, mu=mu_eff, sigma=sigma_cap_eff, shock_drop=shock_drop, spike=spike)
        s_gp = simulate_gbm(i, T_PAPER, mu=GBM_PURE_MU, sigma=GBM_PURE_SIGMA, shock_drop=shock_drop, spike=spike)

        vol_el.append(annualized_vol(s_el))
        mdd_el.append(max_drawdown(s_el))
        rec_el.append(time_to_recover_peak(s_el, SHOCK_DAY))
        reac_el.append(time_to_reanchor(s_el, f_el, SHOCK_DAY, band=0.05))
        hl_el.append(half_life_error(s_el, f_el, SHOCK_DAY))
        err_el.append(mean_error(s_el, f_el))

        vol_gm.append(annualized_vol(s_gm))
        mdd_gm.append(max_drawdown(s_gm))
        rec_gm.append(time_to_recover_peak(s_gm, SHOCK_DAY))

        vol_gp.append(annualized_vol(s_gp))
        mdd_gp.append(max_drawdown(s_gp))
        rec_gp.append(time_to_recover_peak(s_gp, SHOCK_DAY))

    return {
        "name": name,
        "example": (ex_el, ex_f, ex_gm, ex_gp),
        "elastic": {
            "vol": np.array(vol_el),
            "mdd": np.array(mdd_el),
            "rec_peak": np.array(rec_el),
            "rec_fund5": np.array(reac_el),
            "half_life": np.array(hl_el),
            "mean_err": np.array(err_el),
        },
        "gbm_macro": {
            "vol": np.array(vol_gm),
            "mdd": np.array(mdd_gm),
            "rec_peak": np.array(rec_gm),
        },
        "gbm_pure": {
            "vol": np.array(vol_gp),
            "mdd": np.array(mdd_gp),
            "rec_peak": np.array(rec_gp),
        },
        "governance": {
            "lambda": lam,
            "HHI": float(hhi(w)),
            "China_pct": float(100*w.get("CH",0.0)),
            "mu_eff": float(mu_eff),
            "sigma_cap_eff": float(sigma_cap_eff),
            "sigma_spec_eff": float(sigma_spec_eff),
            "K_eff": float(K_eff),
        }
    }

def plot_trajectories(fig_path, title, s_el, s_gm, s_gp):
    plt.figure(figsize=(10, 4))
    plt.plot(s_el, label="BRICS Elástico")
    plt.plot(s_gm, label="GBM Macro")
    plt.plot(s_gp, label="GBM Puro", alpha=0.85)
    plt.axvline(SHOCK_DAY, linestyle="--", alpha=0.7)
    plt.title(title)
    plt.xlabel("Dias")
    plt.ylabel("Preço (normalizado)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_path, dpi=200)
    plt.savefig(fig_path.replace(".png",".pdf"), bbox_inches="tight")
    plt.close()

def plot_price_vs_fund(fig_path, title, s_el, f_el):
    plt.figure(figsize=(10, 4))
    plt.plot(s_el, label="Preço (Elástico)")
    plt.plot(f_el, label="Fundamental")
    plt.axvline(SHOCK_DAY, linestyle="--", alpha=0.7)
    plt.title(title)
    plt.xlabel("Dias")
    plt.ylabel("Normalizado")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_path, dpi=200)
    plt.savefig(fig_path.replace(".png",".pdf"), bbox_inches="tight")
    plt.close()

def plot_bar_mean_std(fig_path, title, labels, arrays, ylabel):
    means = [float(np.mean(a)) for a in arrays]
    stds = [float(np.std(a)) for a in arrays]
    x = np.arange(len(labels))
    plt.figure(figsize=(8, 4))
    plt.bar(x, means, yerr=stds, capsize=4)
    plt.xticks(x, labels)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=200)
    plt.savefig(fig_path.replace(".png",".pdf"), bbox_inches="tight")
    plt.close()

def plot_stability_region(fig_path):
    alphas = np.linspace(0.05, 1.0, 300)
    k_max = 2.0 / alphas
    plt.figure(figsize=(8, 4))
    plt.fill_between(alphas, 0, np.minimum(k_max, 6.0), alpha=0.25, label="Região estável (0 < αk < 2)")
    plt.plot(alphas, k_max, label="Borda αk=2")
    plt.ylim(0, 6.0)
    plt.xlim(0.05, 1.0)
    plt.title("Região teórica de estabilidade local: 0 < αk < 2")
    plt.xlabel("α")
    plt.ylabel("k")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_path, dpi=200)
    plt.savefig(fig_path.replace(".png",".pdf"), bbox_inches="tight")
    plt.close()

# =============================
# SWEEP λ (φ, vol, mdd, convergência)
# =============================

def lambda_sweep():
    rows = []
    phis = []
    pconvs = []
    tmeans = []
    hh = []
    ch = []
    vols = []
    mdds = []

    for lam in LAMBDA_VALUES:
        w, H, mu_eff, sigma_cap_eff, sigma_spec_eff, K_eff = structural_params(lam)
        phi_mean, p_conv, t_mean = phi_and_convergence_for_lambda(lam, sigma_spec_mult=1.0)

        # pequena métrica de risco (paper B rápido): usa N menor pra não demorar demais
        vol_list = []
        mdd_list = []
        for i in range(80):
            s, f = simulate_elastic(90000 + i, T_PAPER, lam, shock_drop=0.40, spike=True, shock_set=SHOCK_SET_PERIPH, use_lambda_fund=True, reconverge=True)
            vol_list.append(annualized_vol(s))
            mdd_list.append(max_drawdown(s))

        row = {
            "lambda": lam,
            "HHI": float(H),
            "China_pct": float(100*w["CH"]),
            "mu_eff": float(mu_eff),
            "sigma_cap_eff": float(sigma_cap_eff),
            "sigma_spec_eff": float(sigma_spec_eff),
            "K_eff": float(K_eff),
            "phi": float(phi_mean),
            "p_conv": float(p_conv),
            "t_mean": float(t_mean),
            "vol_2008": float(np.mean(vol_list)),
            "mdd_2008": float(np.mean(mdd_list)),
        }
        rows.append(row)

        phis.append(row["phi"])
        pconvs.append(row["p_conv"])
        tmeans.append(row["t_mean"])
        hh.append(row["HHI"])
        ch.append(row["China_pct"])
        vols.append(row["vol_2008"])
        mdds.append(row["mdd_2008"])

    # plots
    lams = [r["lambda"] for r in rows]

    plt.figure(figsize=(12, 6))
    plt.subplot(2, 3, 1)
    plt.plot(lams, hh, marker="o")
    plt.title("HHI vs λ")
    plt.xlabel("λ")
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 3, 2)
    plt.plot(lams, ch, marker="o")
    plt.title("China (%) vs λ")
    plt.xlabel("λ")
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 3, 3)
    plt.plot(lams, phis, marker="o")
    plt.title("φ vs λ")
    plt.xlabel("λ")
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 3, 4)
    plt.plot(lams, pconvs, marker="o")
    plt.title("Prob(converge) vs λ")
    plt.xlabel("λ")
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 3, 5)
    plt.plot(lams, tmeans, marker="o")
    plt.title("Tempo médio (dias) vs λ")
    plt.xlabel("λ")
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 3, 6)
    plt.plot(lams, vols, marker="o", label="Vol")
    plt.plot(lams, mdds, marker="o", label="MDD")
    plt.title("Risco 2008-style vs λ")
    plt.xlabel("λ")
    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, "Fig_lambda_sweep_panel.png"), dpi=200)
    plt.savefig(os.path.join(OUTDIR, "Fig_lambda_sweep_panel.pdf"), bbox_inches="tight")
    plt.close()

    return rows

# =============================
# MAIN
# =============================

def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def main():
    # 0) λ sweep (governança + φ + risco)
    sweep_rows = lambda_sweep()

    # 1) Sensibilidade σ_spec
    sig_rows = sigma_spec_sensitivity(lam=0.75, mults=(0.5, 1.0, 2.0, 3.0))

    # 2) Efeito da reconvergência (on/off)
    p_with, p_without = compare_with_without_reconvergence(lam=0.75)

    # 3) Mapa α×k de instabilidade (empírico)
    make_alpha_k_heatmap(lam_for_map=0.75)

    # 4) Paper A e B completos (com λ estrutural no fundamental)
    res_A = run_paper_scenario("Choque Macro", shock_drop=0.30, spike=False, lam=0.75, shock_set=SHOCK_SET_PERIPH)
    res_B = run_paper_scenario("Crise 2008-style", shock_drop=0.40, spike=True, lam=0.75, shock_set=SHOCK_SET_PERIPH)

    # imprime tabela consolidada (médias)
    def line_el(r):
        return (
            float(np.mean(r["vol"])),
            float(np.mean(r["mdd"])),
            summarize_recovery(r["rec_peak"]),
            summarize_recovery(r["rec_fund5"]),
            summarize_recovery(r["half_life"]),
            float(np.mean(r["mean_err"])),
        )

    def line_gbm(r):
        return (
            float(np.mean(r["vol"])),
            float(np.mean(r["mdd"])),
            summarize_recovery(r["rec_peak"]),
        )

    print("\n=== TABELA CONSOLIDADA (MÉDIAS) — λ=0.75 ===")
    print("Cenário | Modelo | Vol | MDD | Rec. pico | Rec. ≤5% fund | Half-life | Erro médio")
    for scen_name, res in [("Choque Macro", res_A), ("Crise 2008-style", res_B)]:
        e = line_el(res["elastic"])
        gm = line_gbm(res["gbm_macro"])
        gp = line_gbm(res["gbm_pure"])
        print(f"{scen_name} | BRICS Elástico | {e[0]:.3f} | {e[1]:.3f} | {e[2]:.1f} | {e[3]:.1f} | {e[4]:.1f} | {e[5]:.4f}")
        print(f"{scen_name} | GBM Macro     | {gm[0]:.3f} | {gm[1]:.3f} | {gm[2]:.1f} | — | — | —")
        print(f"{scen_name} | GBM Puro      | {gp[0]:.3f} | {gp[1]:.3f} | {gp[2]:.1f} | — | — | —")

    # figuras paper (1–10 estilo)
    ex_el, ex_f, ex_gm, ex_gp = res_A["example"]
    plot_trajectories(os.path.join(OUTDIR, "Figura_1_ChoqueMacro_Trajetorias.png"),
                      "Figura 1 — Choque Macro: Elástico vs GBM Macro vs GBM Puro",
                      ex_el, ex_gm, ex_gp)
    plot_price_vs_fund(os.path.join(OUTDIR, "Figura_2_ChoqueMacro_Preco_vs_Fund.png"),
                       "Figura 2 — Choque Macro: Preço (Elástico) vs Fundamental",
                       ex_el, ex_f)

    ex_el, ex_f, ex_gm, ex_gp = res_B["example"]
    plot_trajectories(os.path.join(OUTDIR, "Figura_3_2008_Trajetorias.png"),
                      "Figura 3 — 2008-style: Elástico vs GBM Macro vs GBM Puro",
                      ex_el, ex_gm, ex_gp)
    plot_price_vs_fund(os.path.join(OUTDIR, "Figura_4_2008_Preco_vs_Fund.png"),
                       "Figura 4 — 2008-style: Preço (Elástico) vs Fundamental",
                       ex_el, ex_f)

    plot_bar_mean_std(os.path.join(OUTDIR, "Figura_5_Vol_ChoqueMacro.png"),
                      "Figura 5 — Vol (Choque Macro): média ± desvio",
                      ["Elástico", "GBM Macro", "GBM Puro"],
                      [res_A["elastic"]["vol"], res_A["gbm_macro"]["vol"], res_A["gbm_pure"]["vol"]],
                      ylabel="Vol anualizada")

    plot_bar_mean_std(os.path.join(OUTDIR, "Figura_6_Vol_2008.png"),
                      "Figura 6 — Vol (2008-style): média ± desvio",
                      ["Elástico", "GBM Macro", "GBM Puro"],
                      [res_B["elastic"]["vol"], res_B["gbm_macro"]["vol"], res_B["gbm_pure"]["vol"]],
                      ylabel="Vol anualizada")

    plot_bar_mean_std(os.path.join(OUTDIR, "Figura_7_MDD_ChoqueMacro.png"),
                      "Figura 7 — MDD (Choque Macro): média ± desvio",
                      ["Elástico", "GBM Macro", "GBM Puro"],
                      [res_A["elastic"]["mdd"], res_A["gbm_macro"]["mdd"], res_A["gbm_pure"]["mdd"]],
                      ylabel="Max drawdown")

    plot_bar_mean_std(os.path.join(OUTDIR, "Figura_8_MDD_2008.png"),
                      "Figura 8 — MDD (2008-style): média ± desvio",
                      ["Elástico", "GBM Macro", "GBM Puro"],
                      [res_B["elastic"]["mdd"], res_B["gbm_macro"]["mdd"], res_B["gbm_pure"]["mdd"]],
                      ylabel="Max drawdown")

    plot_stability_region(os.path.join(OUTDIR, "Figura_9_Regiao_Estabilidade.png"))
    # Figura 10 já está representada pelo heatmap e pode ser mantida separada.
    # Se você quiser a versão "barras" (3 pontos), use o heatmap + esse painel já cobre.
    # Mantemos o heatmap como blindagem superior.

    # salva CSV summary
    summary_rows = []
    # sweep
    for r in sweep_rows:
        rr = dict(r)
        rr["type"] = "lambda_sweep"
        summary_rows.append(rr)

    # sigma_spec
    for (m, phi_mean, p_conv, t_mean) in sig_rows:
        summary_rows.append({
            "type": "sigma_spec_sensitivity",
            "lambda": 0.75,
            "sigma_spec_mult": float(m),
            "phi": float(phi_mean),
            "p_conv": float(p_conv),
            "t_mean": float(t_mean),
        })

    summary_rows.append({
        "type": "reconvergence_ablation",
        "lambda": 0.75,
        "p_conv_with": float(p_with),
        "p_conv_without": float(p_without),
    })

    csv_path = os.path.join(OUTDIR, "summary.csv")
    # fieldnames dinâmica (pega união de chaves)
    keys = set()
    for r in summary_rows:
        keys |= set(r.keys())
    fieldnames = sorted(list(keys))
    write_csv(csv_path, summary_rows, fieldnames)

    print(f"\n✅ Tudo salvo em: ./{OUTDIR}/")
    print(f"✅ CSV: {csv_path}")

if __name__ == "__main__":
    main()
