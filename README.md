# 🛰️ Orbit Wars AI

<div align="center">
  <p><strong>Advanced Multi-Agent Model Predictive Control (MPC) & Bayesian Optimization Framework</strong></p>

  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Optimization-Optuna-orange.svg?style=flat-square&logo=analytics" alt="Optimization Framework" />
  <img src="https://img.shields.io/badge/Platform-Kaggle%20Simulation-blueviolet.svg?style=flat-square&logo=kaggle" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat-square" alt="License" />
</div>

---

## 🚀 Advanced Architecture & Mathematical Background

This repository houses the complete evolutionary lifecycle of an autonomous, decentralized simulation agent designed to dominate multi-agent orbital combat environments. The final build discards standard reactive heuristic rules in favor of a continuous **Finite Horizon Model Predictive Control (MPC)** engine.

---

### 1. Real-Time Environmental & Macro-Economic Signatures
Before any tactical calculations are executed, the agent normalizes the spatial layout and economic state of the galaxy into three dynamic metrics:

* **Player Scale Factor ($P$):** Tracks active multi-agent threats in the lobby to adjust risk parameters.
  $$P = \begin{cases} 2.0, & \text{if } \max(\text{owner\_id}) \le 1 \\ 4.0, & \text{otherwise} \end{cases}$$

* **Map Sparsity Scale ($S$):** Evaluates the average geometric Euclidean distance from the primary fleet base to all active hostile nodes.
  $$S = \frac{\sum_{t \in \text{hostiles}} \sqrt{(x_t - x_{\text{base}})^2 + (y_t - y_{\text{base}})^2}}{|\text{hostiles}|}$$

* **Relative Macro-Economic Dominance Index ($\rho$):** Quantifies industrial output relative to the strongest opponent on the board, acting as the agent's core psychological state variable.
  $$\rho = \frac{\text{Total Production}_{\text{Player}}}{\max_{e \in \text{Enemies}} (\text{Total Production}_e)}$$

---

### 2. Continuous Parameter Weighting Heuristics
The agent transforms its static chromosome coefficients ($\alpha, \beta, \gamma$) discovered via Optuna into fluid runtime weights that scale dynamically based on the current economic standing ($\rho$) and spatial constraints ($S$):

* **Distance Penalty Vector ($w_{dis}$):** Applies an exponential expansion curve to limit over-exposure across deep-space voids.
  $$w_{dis} = \max\left(0.10, \min\left(2.00, \alpha_{dis} \cdot e^{\beta_{dis} \cdot S}\right)\right)$$

* **Economic Appetite Vector ($w_{gr}$):** Down-regulates expansion greed as our economic dominance grows to avoid over-extension.
  $$w_{gr} = \max\left(0.05, \min\left(2.50, \frac{\alpha_{gr}}{\rho}\right)\right)$$

* **Fortress Penalty Vector ($w_{ns}$):** Controls aversion to heavily fortified defense garrisons, shifting the bot into an aggressive *Juggernaut* state when dominating.
  $$w_{ns} = \max\left(0.05, \min\left(2.50, \frac{\alpha_{ns} \cdot P}{\rho}\right)\right)$$

* **Fleet Deployment Proportional Pooling ($\text{pool\_perc}$):** Restricts or siphons launch volumes from secondary bases based on multi-faction threat scaling.
  $$\text{pool\_perc} = \max\left(0.45, \min\left(0.98, \gamma_{pool} - (\alpha_{pool} \cdot (P - 2.0)) + (\beta_{pool} \cdot \rho)\right)\right)$$

---

### 3. Decision-Making Matrix (AIS Target Selection)
Every open hostile planet is assigned a scalar utility score using a rational allocation function. The primary heuristic targets the node that maximizes this score:

$$\text{AIS Score} = \frac{(\text{Production}_{\text{target}} \cdot w_{gr}) + 1.0}{(\text{Garrison}_{\text{predicted}} \cdot w_{ns}) + (\text{Distance}_{\text{future}} \cdot w_{dis}) + 1.0}$$

---

### 4. Kinematics & Logarithmic Fleet Velocity
The environment computes fleet velocity ($v$) using a non-linear power-law function tied to total launch mass. The agent actively exploits this curve by clustering strikes to maintain peak speed profiles:

$$v = 1.0 + (v_{\max} - 1.0) \cdot \left(\max\left(0.0, \frac{\ln(\text{ships})}{\ln(1000)}\right)\right)^{1.5}$$

---

### 5. Twin-Queue Model Predictive Control (MPC) Horizon Rollout
To solve greedy lookahead blindness, the final agent splits reality into two distinct priority paths: the **Strategic Utility Queue ($\mathcal{Q}_{AIS}$)** and the **Temporal Path Queue ($\mathcal{Q}_{EASY}$)**.

If the top strategic planet matches the easiest temporal planet ($AIS_1 == EASY_1$), the choice short-circuits. Otherwise, the engine executes a multi-step forward simulation 60 turns into the future ($\Delta T = 60$), evaluating the integrated area under the economic production curve for competing timelines:

$$\text{Integrated Capital Yield} = \sum_{t=0}^{\text{Max\_Horizon}} \text{Total\_Production}(t)$$

The agent then automatically chooses the timeline that optimizes total asset generation, allowing it to capture valueless planets to serve as unblocked forward operating outposts to conquer massive fortresses.

---

## 📁 Repository Blueprint

* **`optimizer/`** — Automated parameter configuration pipelines:
  * `Genetic_algorithm.py` — Generational chromosome crossover, mutation, and selection testing suites.
  * `bayessian.py` — Probabilistic surrogate model exploration engine mapping target parameter boundaries.
  * `optuna_mpc_tuner.py` — Production TPE Sampler actively fine-tuning real-time predictive lookahead weights.

* **`submission/`** — Iterative development archive tracking the evolutionary hierarchy of the AI:
  * `AIS_1.0.py` to `AIS_3.0.py` — Rule-based heuristics, parameter allocation templates, and basic tracking controls.
  * `AIS_4.0.py` to `AIS_5.2.py` — Synchronized cooperative strikes, comet lookahead parameters, and solar obstacle avoidance.
  * `AIS_6.0.py` to `AIS_7.0.py` — Advanced kinematics tracking, relative speed scaling, and early sandbox modeling.
  * `Immune_strategy.py` — **Final Production Build**: The complete Twin-Queue Model Predictive Control agent.

* **`util/`** — Verification, validation, and execution utilities:
  * `play.py` — Local agent runtime compiler and performance simulation coordinator.
  * `validate.py` — Multi-match cross-validation runner calculating win-rates across randomized seeds.

* `ultimate_4way_clash.html` — Interactive HTML canvas visualizer to render live 4-player combat trajectories and debugger metrics.
* `requirements.txt` — Compiled software ecosystem package manifest.

---

## 📊 Optimization Paradigm

| Framework Module | Algorithmic Core | Operational Focus |
| :--- | :--- | :--- |
| **Genetic Algorithm** | Truncation selection, uniform crossover, noisy mutations. | Global strategic parameter discovery. |
| **Bayesian Optimization** | Gaussian Process probabilistic modeling. | Local scalar parameter boundary refinement. |
| **Optuna MPC Tuner** | Tree-structured Parzen Estimators (TPE) + Pruning loops. | Continuous weights for dynamic lookahead trees. |

---

## 🛠️ Installation & Execution Instructions

### 1. Prepare Local Environment
Clone the current codebase and install the required dependencies through the pip manifest:
```bash
git clone [https://github.com/yourusername/orbit-wars.git](https://github.com/yourusername/orbit-wars.git)
cd orbit-wars
pip install -r requirements.txt