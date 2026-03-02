import numpy as np
import matplotlib.pyplot as plt

# =============================
# PARÂMETROS DO SEU MODELO
# =============================
T = 800
ALPHA = 0.5
K = 2.0
MU = 0.04
SIGMA_CAP = 0.12
SIGMA_SPEC = 0.05

np.random.seed(42)

# =============================
# SIMULAÇÃO BASE
# =============================
def simulate_path(initial_error=0.0):
    F = 1.0
    P = F * (1 + initial_error)

    P_series = []
    F_series = []
    error_series = []

    for t in range(T):
        # fundamental evolui
        F *= np.exp((MU/252) + (SIGMA_CAP/np.sqrt(252))*np.random.normal())

        # especulação
        P_spec = P * np.exp(SIGMA_SPEC*np.random.normal())

        # reconvergência
        P_adj = P_spec * (F / (P_spec + 1e-12)) ** K
        P = (1 - ALPHA)*P_spec + ALPHA*P_adj

        P_series.append(P)
        F_series.append(F)
        error_series.append(np.log(P/F))

    return np.array(P_series), np.array(F_series), np.array(error_series)


# =============================
# TESTE 1 — ESTIMAR φ
# =============================
def estimate_phi():
    _, _, e = simulate_path(initial_error=0.3)
    x = e[:-1]
    y = e[1:]

    phi = np.sum(x*y)/np.sum(x*x)
    print("\n=== TESTE φ EMPÍRICO ===")
    print("phi estimado =", round(phi,4))
    print("|phi| < 1 ?", abs(phi) < 1)


# =============================
# TESTE 3 — BACIA DE ATRAÇÃO
# =============================
def basin_of_attraction():
    erros = [-0.9, -0.5, -0.2, 0.2, 0.5, 1.0, 2.0]
    convergiu = []

    print("\n=== BACIA DE ATRAÇÃO ===")
    for e0 in erros:
        _, _, e = simulate_path(initial_error=e0)
        final_error = np.abs(e[-1])
        convergiu.append(final_error < 0.05)
        print(f"Erro inicial {e0: .2f} -> erro final {final_error:.4f}")

    print("Convergências:", convergiu)


# =============================
# TESTE 4 — CONVERGÊNCIA GLOBAL
# =============================
def global_convergence(n=500):
    sucessos = 0
    tempos = []

    for _ in range(n):
        e0 = np.random.uniform(-2, 2)
        _, _, e = simulate_path(initial_error=e0)

        idx = np.where(np.abs(e) < 0.05)[0]
        if len(idx) > 0:
            sucessos += 1
            tempos.append(idx[0])

    print("\n=== CONVERGÊNCIA GLOBAL ===")
    print("Probabilidade de convergir:", round(sucessos/n,4))
    if tempos:
        print("Tempo médio:", round(np.mean(tempos),2))


# =============================
# RODAR
# =============================
if __name__ == "__main__":
    estimate_phi()
    basin_of_attraction()
    global_convergence()
