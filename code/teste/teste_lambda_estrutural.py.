import numpy as np

# =============================
# CONFIG
# =============================
T = 800
SEED = 42

ALPHA = 0.5
K = 2.0

MU_BASE = 0.04
SIGMA_CAP_BASE = 0.12
SIGMA_SPEC = 0.05

LAMBDA = 0.75

BRICS_PIB = {
    "CH": 18.0, "IN": 3.7, "RU": 2.2, "BR": 2.1, "ZA": 0.4,
    "EG": 0.4, "ET": 0.15, "IR": 0.6, "SAU": 1.1, "UAE": 0.5
}

# =============================
# λ HELPERS
# =============================
def pesos_por_pib(pib_dict, lam):
    base = {p: pib_dict[p] ** lam for p in pib_dict}
    s = sum(base.values())
    return {p: base[p] / s for p in base}

def hhi(w):
    return float(sum(v * v for v in w.values()))

W = pesos_por_pib(BRICS_PIB, LAMBDA)
HHI = hhi(W)

# λ entra estruturalmente aqui:
MU_EFF = MU_BASE + 0.01 * W.get("CH", 0.0) + 0.005 * W.get("IN", 0.0)
SIGMA_CAP_EFF = SIGMA_CAP_BASE * (1.0 + 0.5 * HHI)

# =============================
# SIMULAÇÃO (λ estrutural)
# =============================
def simulate_path(rng, initial_error=0.0):
    F = 1.0
    # garante preço positivo mesmo com erro negativo grande
    P = max(1e-12, F * (1.0 + initial_error))

    e = np.empty(T, dtype=float)

    for t in range(T):
        # fundamental macro (com μ_eff e σ_cap_eff)
        F *= np.exp((MU_EFF / 252.0) + (SIGMA_CAP_EFF / np.sqrt(252.0)) * rng.normal())

        # componente espec (sempre positivo)
        P_spec = P * np.exp(SIGMA_SPEC * rng.normal())

        # reconvergência
        P_adj = P_spec * (F / (P_spec + 1e-12)) ** K
        P = (1.0 - ALPHA) * P_spec + ALPHA * P_adj

        # erro logarítmico (protegido)
        e[t] = np.log((P + 1e-12) / (F + 1e-12))

    return e

# =============================
# TESTE 1 — φ empírico
# =============================
def estimate_phi():
    rng = np.random.default_rng(SEED)
    e = simulate_path(rng, initial_error=0.3)
    x = e[:-1]
    y = e[1:]
    phi = float(np.sum(x * y) / (np.sum(x * x) + 1e-12))
    print("\n=== φ EMPÍRICO (com λ) ===")
    print("lambda:", LAMBDA, "| HHI:", round(HHI, 4))
    print("mu_eff:", round(MU_EFF, 5), "| sigma_cap_eff:", round(SIGMA_CAP_EFF, 5))
    print("phi estimado =", round(phi, 4), "| |phi|<1 ?", abs(phi) < 1)

# =============================
# TESTE 3 — Bacia de atração
# =============================
def basin_of_attraction():
    rng = np.random.default_rng(SEED)
    erros = [-0.9, -0.5, -0.2, 0.2, 0.5, 1.0, 2.0]
    ok = []
    print("\n=== BACIA DE ATRAÇÃO (com λ) ===")
    for e0 in erros:
        # usa um RNG “novo” por caso para não contaminar sequência
        r = np.random.default_rng(SEED + int((e0 + 10) * 1000))
        e = simulate_path(r, initial_error=e0)
        final_err = float(abs(e[-1]))
        convergiu = final_err < 0.05
        ok.append(convergiu)
        print(f"Erro inicial {e0: .2f} -> |erro final| {final_err:.4f} -> {convergiu}")
    print("Convergências:", ok)

# =============================
# TESTE 4 — Convergência global
# =============================
def global_convergence(n=500):
    sucessos = 0
    tempos = []

    base_rng = np.random.default_rng(SEED)

    for i in range(n):
        e0 = float(base_rng.uniform(-2, 2))
        rng = np.random.default_rng(SEED + 10000 + i)  # independente por traj
        e = simulate_path(rng, initial_error=e0)

        idx = np.where(np.abs(e) < 0.05)[0]
        if idx.size > 0:
            sucessos += 1
            tempos.append(int(idx[0]))

    print("\n=== CONVERGÊNCIA GLOBAL (com λ) ===")
    print("Probabilidade de convergir:", round(sucessos / n, 4))
    if tempos:
        print("Tempo médio até |erro|<5%:", round(float(np.mean(tempos)), 2), "dias")

if __name__ == "__main__":
    estimate_phi()
    basin_of_attraction()
    global_convergence()
