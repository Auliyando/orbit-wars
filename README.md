<div align="center">
  <h1>🛰️ Orbit Wars AI</h1>
  <p><strong>Advanced Multi-Agent Model Predictive Control (MPC) & Bayesian Optimization Framework</strong></p>

  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/Optimization-Optuna-orange.svg?style=flat-square&logo=analytics" alt="Optimization Framework" />
  <img src="https://img.shields.io/badge/Platform-Kaggle%20Simulation-blueviolet.svg?style=flat-square&logo=kaggle" alt="Platform" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat-square" alt="License" />
</div>

<hr />

<h2>🚀 Advanced Architecture & Mathematical Background</h2>

<p>
  This repository houses the complete evolutionary lifecycle of an autonomous, decentralized simulation agent designed to dominate multi-agent orbital combat environments. The final build discards standard reactive heuristic rules in favor of a continuous <strong>Finite Horizon Model Predictive Control (MPC)</strong> engine.
</p>

<hr />

<h3>1. Real-Time Environmental & Macro-Economic Signatures</h3>
<p>
  Before any tactical calculations are executed, the agent normalizes the spatial layout and economic state of the galaxy into three dynamic metrics:
</p>

<ul>
  <li>
    <strong>Player Scale Factor ($P$):</strong> Tracks active multi-agent threats in the lobby to adjust risk parameters.
    $$P = \begin{cases} 2.0, & \text{if } \max(\text{owner\_id}) \le 1 \\ 4.0, & \text{otherwise} \end{cases}$$
  </li>
  <li>
    <strong>Map Sparsity Scale ($S$):</strong> Evaluates the average geometric Euclidean distance from the primary fleet base to all active hostile nodes.
    $$S = \frac{\sum_{t \in \text{hostiles}} \sqrt{(x_t - x_{\text{base}})^2 + (y_t - y_{\text{base}})^2}}{|\text{hostiles}|}$$
  </li>
  <li>
    <strong>Relative Macro-Economic Dominance Index ($\rho$):</strong> Quantifies industrial output relative to the strongest opponent on the board, acting as the agent's core psychological state variable.
    $$\rho = \frac{\text{Total Production}_{\text{Player}}}{\max_{e \in \text{Enemies}} (\text{Total Production}_e)}$$
  </li>
</ul>

<hr />

<h3>2. Continuous Parameter Weighting Heuristics</h3>
<p>
  The agent transforms its static chromosome coefficients ($\alpha, \beta, \gamma$) discovered via Optuna into fluid runtime weights that scale dynamically based on the current economic standing ($\rho$) and spatial constraints ($S$):
</p>

<ul>
  <li>
    <strong>Distance Penalty Vector ($w_{dis}$):</strong> Applies an exponential expansion curve to limit over-exposure across deep-space voids.
    $$w_{dis} = \max\left(0.10, \min\left(2.00, \alpha_{dis} \cdot e^{\beta_{dis} \cdot S}\right)\right)$$
  </li>
  <li>
    <strong>Economic Appetite Vector ($w_{gr}$):</strong> Down-regulates expansion greed as our economic dominance grows to avoid over-extension.
    $$w_{gr} = \max\left(0.05, \min\left(2.50, \frac{\alpha_{gr}}{\rho}\right)\right)$$
  </li>
  <li>
    <strong>Fortress Penalty Vector ($w_{ns}$):</strong> Controls aversion to heavily fortified defense garrisons, shifting the bot into an aggressive <em>Juggernaut</em> state when dominating.
    $$w_{ns} = \max\left(0.05, \min\left(2.50, \frac{\alpha_{ns} \cdot P}{\rho}\right)\right)$$
  </li>
  <li>
    <strong>Fleet Deployment Proportional Pooling ($\text{pool\_perc}$):</strong> Restricts or siphons launch volumes from secondary bases based on multi-faction threat scaling.
    $$\text{pool\_perc} = \max\left(0.45, \min\left(0.98, \gamma_{pool} - (\alpha_{pool} \cdot (P - 2.0)) + (\beta_{pool} \cdot \rho)\right)\right)$$
  </li>
</ul>

<hr />

<h3>3. Decision-Making Matrix (AIS Target Selection)</h3>
<p>
  Every open hostile planet is assigned a scalar utility score using a rational allocation function. The primary heuristic targets the node that maximizes this score:
</p>

$$\text{AIS Score} = \frac{(\text{Production}_{\text{target}} \cdot w_{gr}) + 1.0}{(\text{Garrison}_{\text{predicted}} \cdot w_{ns}) + (\text{Distance}_{\text{future}} \cdot w_{dis}) + 1.0}$$

<hr />

<h3>4. Kinematics & Logarithmic Fleet Velocity</h3>
<p>
  The environment computes fleet velocity ($v$) using a non-linear power-law function tied to total launch mass. The agent actively exploits this curve by clustering strikes to maintain peak speed profiles:
</p>

$$v = 1.0 + (v_{\max} - 1.0) \cdot \left(\max\left(0.0, \frac{\ln(\text{ships})}{\ln(1000)}\right)\right)^{1.5}$$

<hr />

<h3>5. Twin-Queue Model Predictive Control (MPC) Horizon Rollout</h3>
<p>
  To solve greedy lookahead blindness, the final agent splits reality into two distinct priority paths: the <strong>Strategic Utility Queue ($\mathcal{Q}_{AIS}$)</strong> and the <strong>Temporal Path Queue ($\mathcal{Q}_{EASY}$)</strong>.
</p>
<p>
  If the top strategic planet matches the easiest temporal planet ($AIS_1 == EASY_1$), the choice short-circuits. Otherwise, the engine executes a multi-step forward simulation 60 turns into the future ($\Delta T = 60$), evaluating the integrated area under the economic production curve for competing timelines:
</p>

$$\text{Integrated Capital Yield} = \sum_{t=0}^{\text{Max\_Horizon}} \text{Total\_Production}(t)$$

<p>
  The agent then automatically chooses the timeline that optimizes total asset generation, allowing it to capture valueless planets to serve as unblocked forward operating outposts to conquer massive fortresses.
</p>

<hr />

<h2>📁 Repository Blueprint</h2>

<ul>
  <li><strong><code>optimizer/</code></strong> — Automated parameter configuration pipelines:
    <ul>
      <li><code>Genetic_algorithm.py</code> — Generational chromosome crossover, mutation, and selection testing suites.</li>
      <li><code>bayessian.py</code> — Probabilistic surrogate model exploration engine mapping target parameter boundaries.</li>
      <li><code>optuna_mpc_tuner.py</code> — Production TPE Sampler actively fine-tuning real-time predictive lookahead weights.</li>
    </ul>
  </li>
  <li><strong><code>submission/</code></strong> — Iterative development archive tracking the evolutionary hierarchy of the AI:
    <ul>
      <li><code>AIS_1.0.py</code> to <code>AIS_3.0.py</code> — Rule-based heuristics, parameter allocation templates, and basic tracking controls.</li>
      <li><code>AIS_4.0.py</code> to <code>AIS_5.2.py</code> — Synchronized cooperative strikes, comet lookahead parameters, and solar obstacle avoidance.</li>
      <li><code>AIS_6.0.py</code> to <code>AIS_7.0.py</code> — Advanced kinematics tracking, relative speed scaling, and early sandbox modeling.</li>
      <li><code>Immune_strategy.py</code> — <strong>Final Production Build</strong>: The complete Twin-Queue Model Predictive Control agent.</li>
    </ul>
  </li>
  <li><strong><code>util/</code></strong> — Verification, validation, and execution utilities:
    <ul>
      <li><code>play.py</code> — Local agent runtime compiler and performance simulation coordinator.</li>
      <li><code>validate.py</code> — Multi-match cross-validation runner calculating win-rates across randomized seeds.</li>
    </ul>
  </li>
  <li><code>ultimate_4way_clash.html</code> — Interactive HTML canvas visualizer to render live 4-player combat trajectories and debugger metrics.</li>
  <li><code>requirements.txt</code> — Compiled software ecosystem package manifest.</li>
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
      <td>Truncation selection, uniform crossover, noisy mutations.</td>
      <td>Global strategic parameter discovery.</td>
    </tr>
    <tr>
      <td><strong>Bayesian Optimization</strong></td>
      <td>Gaussian Process probabilistic modeling.</td>
      <td>Local scalar parameter boundary refinement.</td>
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
<p>Clone the current codebase and install the required dependencies through the pip manifest:</p>
<pre><code>git clone https://github.com/yourusername/orbit-wars.git
cd orbit-wars
pip install -r requirements.txt</code></pre>

<h3>2. Run Local Testing Matches</h3>
<p>Launch an isolated local combat instance to inspect active agent behavior frameworks:</p>
<pre><code>python util/play.py</code></pre>

<h3>3. Execute Stability Validation</h3>
<p>Test the agent against baseline static structures across continuous randomized seeds to guarantee crash immunity:</p>
<pre><code>python util/validate.py</code></pre>

<h3>4. Automated Parameter Training</h3>
<p>Engage the Bayesian optimization engine to tune the hyperparameter matrix automatically:</p>
<pre><code>python optimizer/optuna_mpc_tuner.py</code></pre>

<blockquote>
  💡 <strong>Debugging Tip:</strong> Open the standalone <code>ultimate_4way_clash.html</code> dashboard directly inside any browser to trace vector logs, observe planet ownership shifts, and verify target assignment choices frame-by-frame.
</blockquote>