import random
import math
import numpy as np
from kaggle_environments import make

# =====================================================================
# CONTINUOUS PARAMETRIC SEARCH BOUNDARIES
# =====================================================================
# The GA will optimize the slope multipliers governing your fluid function curves
PARAM_BOUNDS = {
    "alpha_dis":  (0.01, 0.40),   # Distance exponential base multiplier
    "beta_dis":   (0.01, 0.10),   # Distance exponential growth rate slope
    "alpha_gr":   (0.20, 2.00),   # Production reward scaling multiplier
    "alpha_ns":   (0.05, 1.50),   # Garrison wall penalty base multiplier
    "gamma_pool": (0.70, 1.00),   # Maximum ceiling baseline for launch pool mass
    "alpha_pool": (0.01, 0.25),   # Player-count safety down-regulation throttle
    "beta_pool":  (0.05, 0.50)    # Endgame phase safety down-regulation throttle
}

# =====================================================================
# GLOBAL EVOLUTIONARY CONFIGURATION MATRIX
# =====================================================================
POPULATION_SIZE = 500   # FIXED: Set to 40 chromosomes. Half (20) will run 4P, half (20) will run 2P.
GENERATIONS = 20       # Number of complete evolutionary lifecycles
MUTATION_RATE = 0.05    # Chance an individual gene encounters mutation noise
MATCHES_PER_GROUP = 4  # Iterations per group matchup to eliminate map luck

# Global mapping array to route chromosomes dynamically during multi-agent matches
CURRENT_TOURNAMENT_CONFIGS = {}

# Persistent cross-turn memory registry to isolate event-driven caching for each player slot
EVAL_STATE_REGISTRY = {
    0: {"last_planet_count": -1, "virtual_blacklist": set()},
    1: {"last_planet_count": -1, "virtual_blacklist": set()},
    2: {"last_planet_count": -1, "virtual_blacklist": set()},
    3: {"last_planet_count": -1, "virtual_blacklist": set()}
}

# =====================================================================
# KINEMATICS ENGINE DEFINITIONS (BALLISTIC COMET-INTEGRATED LOOKAHEAD)
# =====================================================================
def ships_to_speed(ships, max_speed=6.0):
    if ships <= 1: return 1.0
    ratio = math.log(ships) / math.log(1000)
    return 1.0 + (max_speed - 1.0) * (max(0.0, ratio) ** 1.5)

def check_sun_collision(sx, sy, tx, ty):
    cx, cy = 50.0, 50.0
    dx, dy = tx - sx, ty - sy
    len_sq = dx * dx + dy * dy
    if len_sq == 0: return False
    t = max(0.0, min(1.0, ((cx - sx) * dx + (cy - sy) * dy) / len_sq))
    dist = math.sqrt((sx + t * dx - cx)**2 + (sy + t * dy - cy)**2)
    return dist <= 11.5  

def safe_get(obj, key, default=None):
    if hasattr(obj, key): return getattr(obj, key)
    if isinstance(obj, dict): return obj.get(key, default)
    return default

def get_comet_future_pos(obs, comet_id, flight_time):
    raw_comets = safe_get(obs, "comets", [])
    if not raw_comets: return None, None, False
    for c in raw_comets:
        if safe_get(c, "id") == comet_id:
            path = safe_get(c, "path", [])
            path_idx = safe_get(c, "path_index", 0)
            target_idx = int(path_idx + flight_time)
            if target_idx < len(path):
                pos = path[target_idx]
                if isinstance(pos, (list, tuple)): return float(pos[0]), float(pos[1]), True
                elif isinstance(pos, dict): return float(safe_get(pos, "x", 0)), float(safe_get(pos, "y", 0)), True
            return None, None, False
    return None, None, False

def check_planet_collision(sx, sy, tx, ty, obs, source_id, target_id):
    dx, dy = tx - sx, ty - sy
    len_sq = dx * dx + dy * dy
    if len_sq == 0: return False
    
    raw_planets = safe_get(obs, "planets", [])
    normalized_planets = normalize_planets(raw_planets)
    
    for p in normalized_planets:
        p_id, _, px, py, p_radius, _, _ = p
        
        if p_id == source_id or p_id == target_id:
            continue
            
        t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / len_sq))
        closest_x = sx + t * dx
        closest_y = sy + t * dy
        dist = math.sqrt((closest_x - px)**2 + (closest_y - py)**2)
        
        if dist <= (p_radius + 0.5):
            return True
            
    return False

def calculate_exact_ballistic_angle(source_planet, target_planet, num_ships, game_angular_velocity, obs):
    source_id, sx, sy, s_rad = source_planet[0], source_planet[2], source_planet[3], source_planet[4]
    target_id, tx, ty, t_radius = target_planet[0], target_planet[2], target_planet[3], target_planet[4]
    fleet_speed = ships_to_speed(num_ships)
    
    comet_ids = set(safe_get(obs, "comet_planet_ids", []))
    is_comet = target_id in comet_ids
    
    dx = tx - 50.0
    dy = ty - 50.0
    orbital_radius = math.sqrt(dx*dx + dy*dy)
    
    if not is_comet and orbital_radius + t_radius >= 50.0:
        if check_sun_collision(sx, sy, tx, ty): return None, 0.0
        if check_planet_collision(sx, sy, tx, ty, obs, source_id, target_id): return None, 0.0
        return math.atan2(ty - sy, tx - sx), 0.0
        
    current_angle = math.atan2(dy, dx)
    pred_x, pred_y = tx, ty
    flight_time = 0.0
    
    for _ in range(10):
        distance = math.sqrt((pred_x - sx)**2 + (pred_y - sy)**2)
        actual_flight_dist = max(0.1, distance - s_rad)
        flight_time = actual_flight_dist / fleet_speed
        
        if is_comet:
            cx, cy, valid = get_comet_future_pos(obs, target_id, flight_time)
            if not valid: return None, 0.0
            pred_x, pred_y = cx, cy
        else:
            future_angle = current_angle + (game_angular_velocity * flight_time)
            pred_x = 50.0 + orbital_radius * math.cos(future_angle)
            pred_y = 50.0 + orbital_radius * math.sin(future_angle)
            
    if check_sun_collision(sx, sy, pred_x, pred_y): return None, 0.0
    if check_planet_collision(sx, sy, pred_x, pred_y, obs, source_id, target_id): return None, 0.0
    
    return math.atan2(pred_y - sy, pred_x - sx), flight_time

def normalize_planets(raw_planets):
    normalized = []
    for p in raw_planets:
        if hasattr(p, "id"):
            normalized.append([p.id, p.owner, p.x, p.y, p.radius, p.ships, p.production])
        elif isinstance(p, dict):
            normalized.append([
                p.get("id", 0), p.get("owner", 0), p.get("x", 0.0), p.get("y", 0.0),
                p.get("radius", 1.0), p.get("ships", 0), p.get("production", 0)
            ])
        else:
            normalized.append(list(p))
    return normalized

# =====================================================================
# CONTINUOUS COEFFICIENT EVALUATOR WRAPPER
# =====================================================================
def ga_immune_evaluation_agent(obs, configuration=None):
    try:
        global EVAL_STATE_REGISTRY
        player_id = safe_get(obs, "player", 0)
        current_turn = safe_get(obs, "step", 0)
        game_angular_velocity = safe_get(obs, "angular_velocity", 0.035)
        
        if current_turn == 0:
            EVAL_STATE_REGISTRY[player_id] = {"last_planet_count": -1, "virtual_blacklist": set()}
            
        state = EVAL_STATE_REGISTRY[player_id]
        
        raw_planets = safe_get(obs, "planets", [])
        normalized_planets = normalize_planets(raw_planets)
        
        my_planets = [p for p in normalized_planets if p[1] == player_id]
        hostile_planets = [p for p in normalized_planets if p[1] != player_id]
        if not my_planets or not hostile_planets: return []
            
        base_planet = max(my_planets, key=lambda x: x[5])
        is_early_game = len(my_planets) < 4

        # EVENT-DRIVEN CACHE INVALIDATION TRIGGER
        current_my_planet_count = len(my_planets)
        if current_my_planet_count != state["last_planet_count"]:
            state["virtual_blacklist"].clear()
            state["last_planet_count"] = current_my_planet_count

        # -----------------------------------------------------------------
        # LIVE MATHEMATICAL FLUID RUNTIME EQUATIONS
        # -----------------------------------------------------------------
        cfg = CURRENT_TOURNAMENT_CONFIGS[player_id]
        
        max_owner_id = max([p[1] for p in normalized_planets] + [0])
        P = 2.0 if max_owner_id <= 1 else 4.0
        
        total_hostile_dist = sum(math.sqrt((t[2]-base_planet[2])**2 + (t[3]-base_planet[3])**2) for t in hostile_planets)
        S = total_hostile_dist / max(1, len(hostile_planets))
        
        total_planets = len(normalized_planets)
        neutral_nodes = sum(1 for p in normalized_planets if p[1] == -1)
        phi = neutral_nodes / max(1, total_planets)

        w_dis = max(0.10, min(2.00, cfg["alpha_dis"] * math.exp(cfg["beta_dis"] * S)))
        w_gr  = max(0.05, min(1.50, cfg["alpha_gr"] * (phi / math.sqrt(P))))
        w_ns  = max(0.05, min(1.50, cfg["alpha_ns"] * P * ((1.0 - phi) ** 2) + 0.05))
        pool_perc = max(0.45, min(0.98, cfg["gamma_pool"] - (cfg["alpha_pool"] * (P - 2.0) + cfg["beta_pool"] * (1.0 - phi))))
        # -----------------------------------------------------------------

        friendly_inbound_matrix = {}
        hostile_inbound_matrix = {}
        raw_fleets = safe_get(obs, "fleets", [])
        
        for f in raw_fleets:
            f_owner = safe_get(f, "owner")
            f_target = safe_get(f, "target")
            f_ships = safe_get(f, "ships", 0)
            f_turns = safe_get(f, "turns_left", 0)
            
            if f_owner == player_id:
                if f_target not in friendly_inbound_matrix:
                    friendly_inbound_matrix[f_target] = []
                friendly_inbound_matrix[f_target].append((f_ships, f_turns))
            else:
                if f_target not in hostile_inbound_matrix:
                    hostile_inbound_matrix[f_target] = []
                hostile_inbound_matrix[f_target].append((f_ships, f_turns))

        best_target_planet = None
        best_ais_score = -float('inf')
        
        base_buffer = base_planet[5] - 10
        test_launch_mass = max(15, int(base_buffer * pool_perc)) if base_buffer > 0 else 15
        comet_ids = set(safe_get(obs, "comet_planet_ids", []))
        
        for target in hostile_planets:
            if target[2] == 0.0 and target[3] == 0.0: continue
            
            if target[0] in state["virtual_blacklist"]:
                continue 
            
            if is_early_game and target[0] in friendly_inbound_matrix:
                total_friendly_en_route = sum(ships for ships, _ in friendly_inbound_matrix[target[0]])
                max_flight_horizon = max(turns for _, turns in friendly_inbound_matrix[target[0]])
                
                simulated_defense = target[5]
                if target[1] != -1:
                    simulated_defense += target[6] * max_flight_horizon
                    
                if target[0] in hostile_inbound_matrix:
                    for h_ships, h_turns in hostile_inbound_matrix[target[0]]:
                        if h_turns <= max_flight_horizon:
                            simulated_defense += h_ships
                            
                if total_friendly_en_route > simulated_defense:
                    continue
            
            intercept_data = calculate_exact_ballistic_angle(
                base_planet, target, test_launch_mass, game_angular_velocity, obs
            )
            
            if intercept_data[0] is not None:
                angle, f_time = intercept_data
                
                if target[0] in comet_ids:
                    cx, cy, valid = get_comet_future_pos(obs, target[0], f_time)
                    pred_tx, pred_ty = (cx, cy) if valid else (target[2], target[3])
                else:
                    dx = target[2] - 50.0
                    dy = target[3] - 50.0
                    orbital_radius = math.sqrt(dx*dx + dy*dy)
                    current_angle = math.atan2(dy, dx)
                    future_angle = current_angle + (game_angular_velocity * f_time)
                    pred_tx = 50.0 + orbital_radius * math.cos(future_angle)
                    pred_ty = 50.0 + orbital_radius * math.sin(future_angle)
                    
                dx_future = pred_tx - base_planet[2]
                dy_future = pred_ty - base_planet[3]
                dist_future = max(0.1, math.sqrt(dx_future * dx_future + dy_future * dy_future) - base_planet[4])
                
                predicted_enemy_garrison = target[5]
                if target[1] != -1: 
                    predicted_enemy_garrison += target[6] * (math.ceil(f_time) + 1)
                
                score = ((target[6] * w_gr) + 1.0) / ((predicted_enemy_garrison * w_ns) + (dist_future * w_dis) + 1.0)
                
                if score > best_ais_score:
                    best_ais_score = score
                    best_target_planet = target
                    
        if best_target_planet is None: return []
        
        moves = []
        if is_early_game:
            # --- PHASE A: COOPERATIVE LINE-OF-SIGHT STRIKE GATE ---
            _, base_f_time = calculate_exact_ballistic_angle(base_planet, best_target_planet, 15, game_angular_velocity, obs)
            target_owner = best_target_planet[1]
            predicted_enemy_garrison = best_target_planet[5]
            if target_owner != -1:
                predicted_enemy_garrison += best_target_planet[6] * (math.ceil(base_f_time) + 1)
            
            final_needed = int(predicted_enemy_garrison + 1)
            
            strike_team_candidates = []
            total_unblocked_surplus = 0
            
            for my_p in my_planets:
                safe_surplus = int(my_p[5] - 1)
                if safe_surplus <= 0: continue
                
                angle, _ = calculate_exact_ballistic_angle(my_p, best_target_planet, safe_surplus, game_angular_velocity, obs)
                if angle is not None:
                    strike_team_candidates.append((my_p, angle, safe_surplus))
                    total_unblocked_surplus += safe_surplus
            
            if total_unblocked_surplus >= final_needed:
                allocated_ships = 0
                for my_p, angle, safe_surplus in strike_team_candidates:
                    needed_to_complete = final_needed - allocated_ships
                    if needed_to_complete <= 0: break
                    
                    launch_ships = min(safe_surplus, needed_to_complete)
                    
                    if launch_ships < 5:
                        if safe_surplus >= 5: launch_ships = 5
                        else: continue
                    
                    angle, _ = calculate_exact_ballistic_angle(my_p, best_target_planet, launch_ships, game_angular_velocity, obs)
                    if angle is not None:
                        moves.append([int(my_p[0]), float(angle), int(launch_ships)])
                        my_p[5] -= launch_ships
                        allocated_ships += launch_ships
                
                if allocated_ships >= final_needed:
                    state["virtual_blacklist"].add(best_target_planet[0])
        else:
            # --- PHASE B: UNTOUCHED ENDGAME PROPORTIONAL POOLING ---
            for my_p in my_planets:
                if my_p[5] > 5:
                    available_buffer = my_p[5]
                    
                    if my_p[0] == base_planet[0]:
                        launch_ships = int(available_buffer)
                    else:
                        launch_ships = int(available_buffer * pool_perc)
                    
                    if launch_ships >= 5:
                        angle, flight_time = calculate_exact_ballistic_angle(
                            my_p, best_target_planet, launch_ships, game_angular_velocity, obs
                        )
                        
                        if angle is not None:
                            target_owner = best_target_planet[1]
                            target_current_ships = best_target_planet[5]
                            target_production = best_target_planet[6]
                            
                            predicted_enemy_garrison = target_current_ships
                            if target_owner != -1: 
                                predicted_enemy_garrison += target_production * (math.ceil(flight_time) + 1)
                            
                            if launch_ships > (predicted_enemy_garrison):
                                moves.append([int(my_p[0]), float(angle), int(launch_ships)])
                                my_p[5] -= launch_ships
                                state["virtual_blacklist"].add(best_target_planet[0])
                            
        return moves
    except Exception:
        return []

class PureGreedyRuntimeAgent:
    def __init__(self):
        # AIS Evolutionary Optimized Coefficients (Derived from Table II)
        self.W_NS = 0.4555           # Garrison Penalty: How much the bot avoids heavily defended targets
        self.W_GR = 0.8964           # Production Reward: How much the bot values permanent income
        self.W_DIS = 0.6578          # Distance Penalty: How much the bot hates long travel times
        self.POOL_PERC = 0.8730    # Attack Fleet Mass: Percentage of available ships sent out in an attack wave

    def execute_macro_turn(self, obs):
        try:
            player_id = safe_get(obs, "player", 0)
            current_turn = safe_get(obs, "step", 0)
            game_angular_velocity = safe_get(obs, "angular_velocity", 0.035)
            
            raw_planets = safe_get(obs, "planets", [])
            normalized_planets = normalize_planets(raw_planets)
            
            my_planets = [p for p in normalized_planets if p[1] == player_id]
            hostile_planets = [p for p in normalized_planets if p[1] != player_id]
            if not my_planets or not hostile_planets: return []
                
            base_planet = max(my_planets, key=lambda x: x[5])
            is_early_game = len(my_planets) < 4

            # =====================================================================
            # TELEMETRY VALIDATION LAYER: MAP OUTBOUND MIGRATION FIELDS
            # =====================================================================
            friendly_inbound_matrix = {}
            hostile_inbound_matrix = {}
            raw_fleets = safe_get(obs, "fleets", [])
            
            for f in raw_fleets:
                f_owner = safe_get(f, "owner")
                f_target = safe_get(f, "target")
                f_ships = safe_get(f, "ships", 0)
                f_turns = safe_get(f, "turns_left", 0)
                
                if f_owner == player_id:
                    if f_target not in friendly_inbound_matrix:
                        friendly_inbound_matrix[f_target] = []
                    friendly_inbound_matrix[f_target].append((f_ships, f_turns))
                else:
                    if f_target not in hostile_inbound_matrix:
                        hostile_inbound_matrix[f_target] = []
                    hostile_inbound_matrix[f_target].append((f_ships, f_turns))

            # =====================================================================
            # PREDICTIVE AIS TARGET SELECTION LOOP (COMET-INTEGRATED)
            # =====================================================================
            best_target_planet = None
            best_ais_score = -float('inf')
            
            base_buffer = base_planet[5] - 10
            test_launch_mass = max(15, int(base_buffer * self.POOL_PERC)) if base_buffer > 0 else 15
            
            comet_ids = set(safe_get(obs, "comet_planet_ids", []))
            
            for target in hostile_planets:
                if target[2] == 0.0 and target[3] == 0.0: continue
                
                # --- SURGICAL INJECTION: DYNAMIC VIRTUAL CAPTURE LOCKOUT ---
                if is_early_game and target[0] in friendly_inbound_matrix:
                    total_friendly_en_route = sum(ships for ships, _ in friendly_inbound_matrix[target[0]])
                    max_flight_horizon = max(turns for _, turns in friendly_inbound_matrix[target[0]])
                    
                    # Project target garrison states at the exact frame our slowest fleet impacts
                    simulated_defense = target[5]
                    if target[1] != -1:
                        simulated_defense += target[6] * max_flight_horizon
                        
                    # Inject adversary interception intercepts into the lookahead matrix
                    if target[0] in hostile_inbound_matrix:
                        for h_ships, h_turns in hostile_inbound_matrix[target[0]]:
                            if h_turns <= max_flight_horizon:
                                simulated_defense += h_ships
                                
                    # If our current inbound fleet is already guaranteed to conquer it, skip targeting it!
                    if total_friendly_en_route > simulated_defense:
                        continue
                
                intercept_data = calculate_exact_ballistic_angle(
                    base_planet, target, test_launch_mass, game_angular_velocity, obs
                )
                
                if intercept_data[0] is not None:
                    angle, f_time = intercept_data
                    
                    if target[0] in comet_ids:
                        cx, cy, valid = get_comet_future_pos(obs, target[0], f_time)
                        pred_tx, pred_ty = (cx, cy) if valid else (target[2], target[3])
                    else:
                        dx = target[2] - 50.0
                        dy = target[3] - 50.0
                        orbital_radius = math.sqrt(dx*dx + dy*dy)
                        current_angle = math.atan2(dy, dx)
                        future_angle = current_angle + (game_angular_velocity * f_time)
                        pred_tx = 50.0 + orbital_radius * math.cos(future_angle)
                        pred_ty = 50.0 + orbital_radius * math.sin(future_angle)
                        
                    dx_future = pred_tx - base_planet[2]
                    dy_future = pred_ty - base_planet[3]
                    dist_future = max(0.1, math.sqrt(dx_future * dx_future + dy_future * dy_future) - base_planet[4])
                    
                    predicted_enemy_garrison = target[5]
                    if target[1] != -1: 
                        predicted_enemy_garrison += target[6] * math.ceil(f_time)
                    
                    score = ((target[6] * self.W_GR) + 1.0) / ((predicted_enemy_garrison * self.W_NS) + (dist_future * self.W_DIS) + 1.0)
                    
                    if score > best_ais_score:
                        best_ais_score = score
                        best_target_planet = target
                        
            if best_target_planet is None: return []
            
            # =====================================================================
            # FLEET DISPATCH PROTOCOL LAYER
            # =====================================================================
            moves = []
            for my_p in my_planets:
                if is_early_game:
                    # --- PHASE A: SURGICAL REQUIREMENT + 1 LAUNCH ---
                    garrison_guess = int(best_target_planet[5] + 1)
                    angle, flight_time = calculate_exact_ballistic_angle(
                        my_p, best_target_planet, garrison_guess, game_angular_velocity, obs
                    )
                    
                    if angle is not None:
                        target_owner = best_target_planet[1]
                        target_current_ships = best_target_planet[5]
                        target_production = best_target_planet[6]
                        
                        predicted_enemy_garrison = target_current_ships
                        if target_owner != -1: 
                            predicted_enemy_garrison += target_production * math.ceil(flight_time)
                        
                        final_needed = int(predicted_enemy_garrison + 1)
                        
                        if int(my_p[5] - 1) >= final_needed:
                            angle, flight_time = calculate_exact_ballistic_angle(
                                my_p, best_target_planet, final_needed, game_angular_velocity, obs
                            )
                            if angle is not None:
                                moves.append([int(my_p[0]), float(angle), int(final_needed)])
                                my_p[5] -= final_needed
                else:
                    # --- PHASE B: UNTOUCHED CLASSIC PROPORTIONAL POOLING ---
                    if my_p[5] > 5:
                        available_buffer = my_p[5]
                        
                        if my_p[0] == base_planet[0]:
                            launch_ships = int(available_buffer)
                        else:
                            launch_ships = int(available_buffer * self.POOL_PERC)
                        
                        if launch_ships >= 5:
                            angle, flight_time = calculate_exact_ballistic_angle(
                                my_p, best_target_planet, launch_ships, game_angular_velocity, obs
                            )
                            
                            if angle is not None:
                                target_owner = best_target_planet[1]
                                target_current_ships = best_target_planet[5]
                                target_production = best_target_planet[6]
                                
                                predicted_enemy_garrison = target_current_ships
                                if target_owner != -1: 
                                    predicted_enemy_garrison += target_production * math.ceil(flight_time)
                                
                                if launch_ships > (predicted_enemy_garrison):
                                    moves.append([int(my_p[0]), float(angle), int(launch_ships)])
                                    my_p[5] -= launch_ships
                                
            return moves
        except Exception:
            return []

# =====================================================================
# GENETIC ALGORITHM PROCEDURAL MATING BLOCKS
# =====================================================================
def create_random_chromosome():
    chromosome = {}
    for param, bounds in PARAM_BOUNDS.items():
        chromosome[param] = round(random.uniform(bounds[0], bounds[1]), 4)
    return chromosome

def crossover_uniform(parent_a, parent_b):
    child = {}
    for param in PARAM_BOUNDS.keys():
        child[param] = parent_a[param] if random.random() < 0.5 else parent_b[param]
    return child

def mutate_gaussian(chromosome):
    for param, bounds in PARAM_BOUNDS.items():
        if random.random() < MUTATION_RATE:
            scale = (bounds[1] - bounds[0]) * 0.12
            noise = np.random.normal(0, scale)
            mutated_value = chromosome[param] + noise
            chromosome[param] = round(max(bounds[0], min(bounds[1], mutated_value)), 4)
    return chromosome

# =====================================================================
# EXECUTIVE EVOLUTIONARY LOOP RUNNER (DYNAMIC BALANCED SPLIT)
# =====================================================================
def run_evolutionary_optimization():
    global CURRENT_TOURNAMENT_CONFIGS
    # env = make("orbit_wars", debug=False)
    
    # Validation Gate: Ensure population size can be divided perfectly into halves
    if POPULATION_SIZE % 2 != 0:
        raise ValueError("POPULATION_SIZE must be an even number to divide 50/50 between 2P and 4P matches.")
        
    print(f"Initializing Fluid Curve DNA Pool with {POPULATION_SIZE} Chromosomes... 🌱")
    population = [create_random_chromosome() for _ in range(POPULATION_SIZE)]
    
    for generation in range(GENERATIONS):
        print(f"\n====== EXECUTING CURVE OPTIMIZATION LIFECYCLE {generation + 1}/{GENERATIONS} ======")
        fitness_scores = [0] * POPULATION_SIZE
        
        matchup_indices = list(range(POPULATION_SIZE))
        random.shuffle(matchup_indices)
        
        # --- DYNAMIC 50/50 POOL SPLITTING LAYER ---
        midpoint = POPULATION_SIZE // 2
        four_player_pool = matchup_indices[:midpoint]
        two_player_pool = matchup_indices[midpoint:]
        
        # 1. RUN ALL 4-PLAYER MATCHES (Iterates dynamically over exactly half the population)
        for i in range(0, len(four_player_pool), 4):
            group_slots = four_player_pool[i:i+4]
            # Safety fallback for rounding remainders
            if len(group_slots) < 4: continue
            
            # print(f" Group Arena (Strict 4P Mode): Chromosomes {group_slots}")
            
            for slot_id in range(4):
                CURRENT_TOURNAMENT_CONFIGS[slot_id] = population[group_slots[slot_id]]
                
            for match in range(MATCHES_PER_GROUP):
                env = make("orbit_wars", debug=False)
                steps = env.run([ga_immune_evaluation_agent] * 4)
                final_planet_state = steps[-1][0]['observation']['planets']
                
                for slot_id in range(4):
                    controlled_nodes = sum(1 for p in final_planet_state if (p.owner if hasattr(p, 'owner') else p[1]) == slot_id)
                    pop_idx = group_slots[slot_id]
                    fitness_scores[pop_idx] += controlled_nodes

        # 2. RUN ALL 2-PLAYER MATCHES (Iterates dynamically over exactly the other half)
        for i in range(0, len(two_player_pool), 2):
            group_slots = two_player_pool[i:i+2]
            if len(group_slots) < 2: continue
            
            # print(f" Group Arena (Strict 2P Mode): Chromosomes {group_slots}")
            
            # Map configuration properties to active slots, wipe references for slots 2 and 3
            CURRENT_TOURNAMENT_CONFIGS[0] = population[group_slots[0]]
            CURRENT_TOURNAMENT_CONFIGS[1] = population[group_slots[1]]
            CURRENT_TOURNAMENT_CONFIGS[2] = None
            CURRENT_TOURNAMENT_CONFIGS[3] = None
                    
            for match in range(MATCHES_PER_GROUP):
                env = make("orbit_wars", debug=False)
                steps = env.run([ga_immune_evaluation_agent] * 2)
                final_planet_state = steps[-1][0]['observation']['planets']
                
                for slot_id in range(2):
                    controlled_nodes = sum(1 for p in final_planet_state if (p.owner if hasattr(p, 'owner') else p[1]) == slot_id)
                    pop_idx = group_slots[slot_id]
                    fitness_scores[pop_idx] += controlled_nodes

        # Generation Assessment Sorting
        ranked_population_data = sorted(zip(population, fitness_scores), key=lambda x: x[1], reverse=True)
        population = [item[0] for item in ranked_population_data]
        alpha_score = ranked_population_data[0][1]
        
        print(f"\n[Generation {generation + 1} Curve Extraction Summary]")
        print(f" Maximum Team Planet Capture Yield: {alpha_score}")
        print(f" Dominant Functional Curve DNA: {population[0]}")
        
        # Elitism Shield Assignment
        next_generation = population[:POPULATION_SIZE // 2]
        
        # Repopulate Empty Pool Half
        while len(next_generation) < POPULATION_SIZE:
            parent_1, parent_2 = random.sample(population[:POPULATION_SIZE // 2], 2)
            child_chromosome = crossover_uniform(parent_1, parent_2)
            child_chromosome = mutate_gaussian(child_chromosome)
            next_generation.append(child_chromosome)
            
        population = next_generation

    print("\n=====================================================================")
    print("🏆 META-OPTIMIZATION COMPLETE! FLUID SLOPE COEFFICIENTS DISCOVERED 🏆")
    print("=====================================================================")
    for key, value in population[0].items():
        print(f"    self.{key} = {value}")
    print("=====================================================================")

if __name__ == "__main__":
    run_evolutionary_optimization()