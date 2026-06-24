# 🛰️ Orbit Wars AI

Welcome to **Orbit Wars**, a repository dedicated to developing, optimizing, and evaluating intelligent agents (AIs) designed to dominate the orbital battlefield. This project utilizes advanced optimization frameworks—including Genetic Algorithms, Bayesian Optimization, and Optuna—to tune agent parameters across iterative version drops (`v1.0` through `v7.0`).

## 📁 Repository Structure

Here is a quick look at how the workspace is structured:

```text
orbit-wars/
├── optimizer/                  # Hyperparameter tuning engines
│   ├── Genetic_algorithm.py    # GA-based agent optimization
│   └── bayessian.py            # Bayesian optimization workflows
├── submission/                 # Evolutionary agent iterations
│   ├── AIS_1.0.py              # Baseline AI agent
│   ├── AIS_2.0.py - 2.1.py     # Rule-based enhancements & Parameter Tuning
│   ├── AIS_3.0.py              # Ship Calculation and Overkill stopper
│   ├── AIS_4.0.py - 4.3.py     # Coordinated attack, multi planet targeting, overkill and obstacle avoidance
│   ├── AIS_5.0.py - 5.2.py     # Baseline extrapolation coefficients
│   ├── AIS_6.0.py              # Production rate based coefficients
│   └── AIS_7.0.py              # Adding Model Predictive Control (MPC)
├── util/                       # Simulation and debugging suite
│   ├── play.py                 # Game execution & manual play runner
│   └── validate.py             # Validation scripts to check win rate
├── ultimate_4way_clash.html    # Interactive HTML local visualizer for matches
└── requirements.txt            # Python dependencies
```
🚀 Getting Started
1. Installation

Clone this repository and ensure you have all mandatory dependencies cooked up by installing the requirements file:
Bash

    pip install -r requirements.txt

Note: The optimization architecture natively leverages frameworks like Optuna for automated parameter space exploration.

2. Simulating Matches

To test your agents locally or simulate battles between different script versions, run the match simulator inside the utilities folder:
Bash

    python util/play.py

3. Verification & CI/CD

To ensure your agent logic complies with match constraints and doesn't crash during runtime execution, use the validation script:
Bash

    python util/validate.py

🧬 Optimization Framework

The optimizer/ directory contains workflows designed to maximize agent win rates through smart search strategies rather than brute force.
Optimizer Model	Description	Primary Use Case
Genetic Algorithm	Uses selection, crossover, and mutation to evolve state-weight parameters over generations.	Global macro-strategy exploration
Bayesian Optimization	Builds a probabilistic model of the objective function to sample promising parameter bounds efficiently.	Fine-tuning continuous action thresholds
Optuna Tuner	Harnesses state-of-the-art automated parameter search algorithms with dynamic pruning loops.	Multi-agent coordinate optimization
📊 Visualizing Results

The project includes an interactive web dashboard (ultimate_4way_clash.html). Open this file directly in any modern browser to watch 4-way battle simulations, analyze spatial trajectories, and debug agent target selection visually.