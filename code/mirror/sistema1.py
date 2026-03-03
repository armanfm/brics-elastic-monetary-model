import numpy as np
import matplotlib.pyplot as plt

# ==============================
# CONFIG
# ==============================
T = 2000
UPDATE_INTERVAL = 63
SHOCK_DAY = 1000

ALPHA = 0.5
K = 2.0
LAMBDA = 0.6
SIGMA_SPEC = 0.04

GDP_GROWTH = 0.04
GDP_SHOCK = 0.15

# Queima espelho: queima proporcional à perda detectada
BURN_RATIO = 1.0  # 1 = queima 100% proporcional à perda

BRICS_PIB = {
    "CH": 18.0, "IN": 3.7, "RU": 2.2, "BR": 2.1, "ZA": 0.4,
    "EG": 0.4, "ET": 0.15, "IR": 0.6, "SAU": 1.1, "UAE": 0.5
}

countries = list(BRICS_PIB.keys())
weights = np.array([BRICS_PIB[c]**LAMBDA for c in countries])
weights /= weights.sum()

def simulate_mirror_burn(seed=42):
    rng = np.random.default_rng(seed)

    true_cap = np.array([3*BRICS_PIB[c] for c in countries], dtype=float)
    reported_cap = np.sum(weights * true_cap)

    supply = reported_cap
    P = 1.0

    hist_p, hist_f, hist_s = [], [], []

    for t in range(T):

        # Crescimento real diário
        true_cap *= np.exp(GDP_GROWTH/252)

        # Choque
        if t == SHOCK_DAY:
            true_cap *= (1 - GDP_SHOCK)

        # Atualização trimestral
        if t % UPDATE_INTERVAL == 0 and t > 0:
            new_cap = np.sum(weights * true_cap)
            delta = (new_cap / reported_cap) - 1

            # Se houve contração → queima espelho
            if delta < 0:
                supply *= (1 + delta * BURN_RATIO)

            reported_cap = new_cap

        F = reported_cap / supply

        P_spec = P * np.exp(rng.normal(0, SIGMA_SPEC))
        P_adj = P_spec * (F / (P_spec + 1e-12))**K
        P = (1 - ALPHA)*P_spec + ALPHA*P_adj

        hist_p.append(P)
        hist_f.append(F)
        hist_s.append(supply)

    return np.array(hist_p), np.array(hist_f), np.array(hist_s)

p, f, s = simulate_mirror_burn()

plt.figure(figsize=(12,8))
plt.subplot(2,1,1)
plt.plot(p, label="Preço")
plt.step(range(T), f, where="post", label="Fundamental")
plt.axvline(SHOCK_DAY, color="red", linestyle="--")
plt.legend()
plt.title("Modelo Queima Espelho")

plt.subplot(2,1,2)
plt.plot(s, label="Supply")
plt.legend()
plt.show()

print("Drawdown:", np.min(p/np.maximum.accumulate(p)-1))
