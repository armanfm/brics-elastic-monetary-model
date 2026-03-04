import numpy as np
import matplotlib.pyplot as plt

# =================================================================
# 1. CONFIGURAÇÕES E DADOS BASE (BRICS-10)
# =================================================================
PIB = {
    "CH": 18.0, "IN": 3.7, "RU": 2.2, "BR": 2.1,
    "ZA": 0.4, "EG": 0.4, "ET": 0.15, "IR": 0.6,
    "SAU": 1.1, "UAE": 0.5
}
countries = list(PIB.keys())
N = len(countries)

# Parâmetros do seu Modelo Elástico
LAMBDA = 0.75  # Dial de Governança
ALPHA = 0.5    # Velocidade de ajuste
K = 2.0        # Força da elasticidade
T = 252 * 5    # Horizonte de 5 anos
N_SIM = 100    # Número de simulações Monte Carlo

# Pesos baseados no PIB^lambda (conforme seu paper)
weights_raw = np.array([PIB[c]**LAMBDA for c in countries])
weights = weights_raw / weights_raw.sum()

# =================================================================
# 2. ULTRA DEEP: CONSTRUÇÃO DA MATRIZ DE CONTÁGIO (CORRIGIDA)
# =================================================================
def get_stable_cholesky(n, corr_base=0.2):
    # Cria matriz de correlação base
    matrix = np.eye(n) + corr_base
    np.fill_diagonal(matrix, 1.0)
    
    # Adiciona contágio específico (China e Índia)
    ch_idx, in_idx = countries.index("CH"), countries.index("IN")
    for i in range(n):
        if i != ch_idx: matrix[ch_idx, i] = matrix[i, ch_idx] = 0.5
        if i != in_idx: matrix[in_idx, i] = matrix[i, in_idx] = 0.4

    # --- CORREÇÃO TÉCNICA (Evita o LinAlgError) ---
    epsilon = 1e-8
    matrix += np.eye(n) * epsilon # Jitter na diagonal
    
    try:
        return np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError:
        # Se falhar, força a matriz a ser Positiva Definida via Autovalores
        labels, vecs = np.linalg.eigh(matrix)
        labels = np.maximum(labels, epsilon)
        matrix_fixed = vecs @ np.diag(labels) @ vecs.T
        return np.linalg.cholesky(matrix_fixed)

L = get_stable_cholesky(N)

# =================================================================
# 3. MOTOR DE SIMULAÇÃO
# =================================================================
def run_simulation(use_contagion=True):
    # Estado inicial
    cap = np.array([PIB[c] for c in countries], dtype=float)
    supply = np.sum(weights * cap)
    P = 1.0
    hist_p = []
    
    for t in range(T):
        # Choques Correlacionados (Contágio) ou Independentes
        z = np.random.normal(0, 1, N)
        shocks = (L @ z) if use_contagion else z
        
        # Evolução do Capital Real (Macro)
        dt = 1/252
        # mu=4%, sigma=12% (conforme seus parâmetros originais)
        growth = np.exp((0.04 - 0.5 * 0.12**2) * dt + 0.12 * np.sqrt(dt) * shocks)
        cap *= growth
        
        # Fundamental (F_t)
        F_t = np.sum(weights * cap) / supply
        
        # Componente Especulativo (Ruído de curto prazo)
        P_spec = P * np.exp(np.random.normal(0, 0.01)) 
        
        # MECANISMO ELÁSTICO (A alma do seu paper)
        # P_adj = P_spec * (F/P_spec)^K
        P_adj = P_spec * (F_t / (P_spec + 1e-12))**K
        P = (1 - ALPHA) * P_spec + ALPHA * P_adj
        
        hist_p.append(P)
        
    return np.array(hist_p)

# =================================================================
# 4. EXECUÇÃO E VISUALIZAÇÃO
# =================================================================
print("Iniciando Simulações Monte Carlo (Ultra Deep)...")
res_contagio = np.array([run_simulation(True) for _ in range(N_SIM)])
res_baseline = np.array([run_simulation(False) for _ in range(N_SIM)])

plt.figure(figsize=(12, 6))
time = np.arange(T)

# Plot Com Contágio
plt.plot(time, np.mean(res_contagio, axis=0), color='firebrick', lw=2, label="Com Contágio (Ultra Deep)")
plt.fill_between(time, np.percentile(res_contagio, 5, axis=0), np.percentile(res_contagio, 95, axis=0), color='firebrick', alpha=0.15)

# Plot Sem Contágio
plt.plot(time, np.mean(res_baseline, axis=0), color='royalblue', lw=2, ls='--', label="Sem Contágio (Independente)")

plt.title("Resiliência da Moeda BRICS sob Contágio Sistêmico\n(Mecanismo Elástico: alpha=0.5, k=2.0)", fontsize=14)
plt.xlabel("Dias Úteis")
plt.ylabel("Preço Relativo")
plt.legend()
plt.grid(True, alpha=0.3)

# Estatísticas de Estresse
vol_c = np.mean([np.std(np.diff(np.log(p))) * np.sqrt(252) for p in res_contagio])
vol_b = np.mean([np.std(np.diff(np.log(p))) * np.sqrt(252) for p in res_baseline])

print(f"\nRESULTADOS:")
print(f"Volatilidade Baseline: {vol_b:.2%}")
print(f"Volatilidade c/ Contágio: {vol_c:.2%}")
print(f"Risco de Cauda (95% percentile no final): {np.percentile(res_contagio[:,-1], 5):.4f}")

plt.show()
