<div align="center">
  <h1>🛰️ Orbit Wars AI</h1>
  <p><strong>An advanced Autonomous Multi-Agent Predictive Simulation Framework</strong></p>

  <!-- Status Badges -->
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Optimization-Optuna-orange.svg?style=flat-square&logo=analytics" alt="Optimization Framework" />
  <img src="https://img.shields.io/badge/Platform-Kaggle%20Simulation-blueviolet.svg?style=flat-square&logo=kaggle" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat-square" alt="License" />
</div>

<hr />

<h2>🚀 Advanced Architecture Overview</h2>

<p>
  This repository tracks the evolutionary development of an intelligent, decentralized game agent optimized to dominate real-time orbital simulation battlefields. The engine transitions away from rigid, static rules into an advanced <strong>Model Predictive Control (MPC)</strong> framework guided by a continuous macro-economic feedback loop.
</p>

<h3>1. Relative Macro-Economic Dominance Vector ($\rho$)</h3>
<p>
  The agent completely discards basic temporal phase metrics in favor of tracking its real-time industrial production scaling coefficient against the most dominant adversary on the board:
</p>
$$\rho = \frac{\text{Total Production}_{\text{Player}}}{\max_{e \in \text{Enemies}} (\text{Total Production}_e)}$$
<p>
  This value modulates overall faction psychology. When lagging behind ($\rho < 1.0$), expansion parameters automatically spike to rapidly claim high-production clusters. When leading ($\rho > 1.0$), the system drops its defense penalties and shifts into a hyper-aggressive juggernaut state to deliver decisive finishing blows.
</p>

<h3>2. Twin-Queue Finite Horizon Rollout</h3>
<p>
  Targets are filtered simultaneously into two dynamically sorted structures: a <strong>Strategic Utility Queue ($\mathcal{Q}_{AIS}$)</strong> based on long-term net asset gains, and a <strong>Temporal Path Queue ($\mathcal{Q}_{EASY}$)</strong> based purely on flight-time acquisition costs. The engine branches its lookup timeline 60 steps forward into a virtual sandbox array, picking the exact trajectory that maximizes integrated ship capital generation over the predictive horizon.
</p>

<hr />

<h2>📁 Repository Blueprint</h2>

<p>The internal organization of the <code>orbit-wars</code> repository is structured as follows[cite: 1]:</p>

<ul>
  <li><strong><code>optimizer/</code></strong> — Automated parameter configuration pipelines[cite: 1]:
    <ul>
      <li><code>Genetic_algorithm.py</code> — Generational chromosome crossover, mutation, and selection testing suites[cite: 1].</li>
      <li><code>bayessian.py</code> — Probabilistic surrogate model exploration engine mapping target parameter boundaries[cite: 1].</li>
      <li><code>optuna_mpc_tuner.py</code> — Production TPE Sampler actively fine-tuning real-time predictive lookout weights.</li>
    </ul>
  </li>
  <li><strong><code>submission/</code></strong> — Iterative development archive tracking the evolutionary hierarchy of the AI[cite: 1]:
    <ul>
      <li><code>AIS_1.0.py</code> to <code>AIS_3.0.py</code> — Rule-based heuristics, parameter allocation templates, and basic tracking controls[cite: 1].</li>
      <li><code>AIS_4.0.py</code> to <code>AIS_5.2.py</code> — Synchronized cooperative strikes, comet lookahead parameters, and solar obstacle avoidance[cite: 1].</li>
      <li><code>AIS_6.0.py</code> to <code>AIS_7.0.py</code> — Advanced kinematics tracking, relative speed scaling, and early sandbox modeling[cite: 1].</li>
      <li><code>Immune_strategy.py</code> — <strong>Final Production Build</strong>: The complete Twin-Queue Model Predictive Control agent.</li>
    </ul>
  </li>
  <li><strong><code>util/</code></strong> — Verification, validation, and execution utilities[cite: 1]:
    <ul>
      <li><code>play.py</code> — Local agent runtime compiler and performance simulation coordinator[cite: 1].</li>
      <li><code>validate.py</code> — Multi-match cross-validation runner calculating win-rates across randomized seeds[cite: 1].</li>
    </ul>
  </li>
  <li><code>ultimate_4way_clash.html</code> — Interactive HTML canvas visualizer to render live 4-player combat trajectories and debugger metrics[cite: 1].</li>
  <li><code>requirements.txt</code> — Compiled software ecosystem package manifest[cite: 1].</li>
</ul>

<hr />

<h2>📊 Optimization Paradigm</h2>

<table width="100%">
  <thead>
    <tr>
      <th align="left">Framework Module</th>
      <th align="left">Algorithmic Core</th>
      <th align="left">Operational Focus</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Genetic Algorithm</strong></td>
      <td>Truncation selection, uniform crossover, noisy mutations[cite: 1].</td>
      <td>Global strategic parameter discovery[cite: 1].</td>
    </tr>
    <tr>
      <td><strong>Bayesian Optimization</strong></td>
      <td>Gaussian Process probabilistic modeling[cite: 1].</td>
      <td>Local scalar parameter boundary refinement[cite: 1].</td>
    </tr>
    <tr>
      <td><strong>Optuna MPC Tuner</strong></td>
      <td>Tree-structured Parzen Estimators (TPE) + Pruning loops.</td>
      <td>Continuous weights for dynamic lookahead trees.</td>
    </tr>
  </tbody>
</table>

<hr />

<h2>🛠️ Installation & Execution Instructions</h2>

<h3>1. Prepare Local Environment</h3>
<p>Clone the current codebase and install the required dependencies through the pip manifest[cite: 1]:</p>
<pre><code>git clone https://github.com/yourusername/orbit-wars.git
cd orbit-wars
pip install -r requirements.txt</code></pre>

<h3>2. Run Local Testing Matches</h3>
<p>Launch an isolated local combat instance to inspect active agent behavior frameworks[cite: 1]:</p>
<pre><code>python util/play.py</code></pre>

<h3>3. Execute Stability Validation</h3>
<p>Test the agent against baseline static structures across continuous randomized seeds to guarantee crash immunity[cite: 1]:</p>
<pre><code>python util/validate.py</code></pre>

<h3>4. Automated Parameter Training</h3>
<p>Engage the Bayesian optimization engine to tune the hyperparameter matrix automatically:</p>
<pre><code>python optimizer/optuna_mpc_tuner.py</code></pre>

<blockquote>
  💡 <strong>Debugging Tip:</strong> Open the standalone <code>ultimate_4way_clash.html</code> dashboard directly inside any browser to trace vector logs, observe planet ownership shifts, and verify target assignment choices frame-by-frame[cite: 1].
</blockquote>