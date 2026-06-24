import os
import math
import numpy as np
from kaggle_environments import make

TOTAL_VALIDATION_MATCHES = 100  # Number of iterations per matchup bracket

# =====================================================================
# CORE RELATIVE KINEMATICS ENGINE (SHARED UTILITIES)
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
    return None, None, False

def check_planet_collision(sx, sy, tx, ty, obs, source_id, target_id):
    dx, dy = tx - sx, ty - sy
    len_sq = dx * dx + dy * dy
    if len_sq == 0: return False
    raw_planets = safe_get(obs, "planets", [])
    normalized_planets = normalize_planets(raw_planets)
    for p in normalized_planets:
        p_id, _, px, py, p_radius, _, _ = p
        if p_id == source_id or p_id == target_id: continue
        t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / len_sq))
        closest_x = sx + t * dx
        closest_y = sy + t * dy
        dist = math.sqrt((closest_x - px)**2 + (closest_y - py)**2)
        if dist <= (p_radius + 0.5): return True
    return False

def calculate_exact_ballistic_angle(source_planet, target_planet, num_ships, game_angular_velocity, obs):
    source_id, sx, sy, s_rad = source_planet[0], source_planet[2], source_planet[3], source_planet[4]
    target_id, tx, ty, t_radius = target_planet[0], target_planet[2], target_planet[3], target_planet[4]
    fleet_speed = ships_to_speed(num_ships)
    comet_ids = set(safe_get(obs, "comet_planet_ids", []))
    is_comet = target_id in comet_ids
    dx, dy = tx - 50.0, ty - 50.0
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
        flight_time = max(0.1, distance - s_rad) / fleet_speed
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
    return [[p.id, p.owner, p.x, p.y, p.radius, p.ships, p.production] if hasattr(p, "id") else list(p) for p in raw_planets]


# ============================================================================
# BOT 1 DEFINITION: CONTINUOUS PARAMETRIC AGENT (ALPHA VARIANT)
# ============================================================================
class ContinuousAgentAlpha:
    def __init__(self):
        # =====================================================================
        # PASTE YOUR OPTUNA MAX-POTENTIAL TUNING COEFFS HERE
        # =====================================================================
        self.alpha_dis = 0.2251
        self.beta_dis = 0.0201
        self.alpha_gr = 1.7147
        self.alpha_ns = 1.0603
        self.gamma_pool = 0.7115
        self.alpha_pool = 0.2015
        self.beta_pool = -0.3586
        # =====================================================================
        
        self.last_my_planet_count = -1
        self.virtual_blacklist = set()

    def execute_macro_turn(self, obs):
        try:
            player_id = safe_get(obs, "player", 0)
            current_turn = safe_get(obs, "step", 0)
            game_angular_velocity = safe_get(obs, "angular_velocity", 0.035)
            
            if current_turn == 0:
                self.last_my_planet_count = -1
                self.virtual_blacklist.clear()

            raw_planets = safe_get(obs, "planets", [])
            normalized_planets = normalize_planets(raw_planets)
            my_planets = [p for p in normalized_planets if p[1] == player_id]
            hostile_planets = [p for p in normalized_planets if p[1] != player_id]
            if not my_planets or not hostile_planets: return []
                
            base_planet = max(my_planets, key=lambda x: x[5])
            is_early_game = len(my_planets) < 4

            current_my_planet_count = len(my_planets)
            if current_my_planet_count != self.last_my_planet_count:
                self.virtual_blacklist.clear()
                self.last_my_planet_count = current_my_planet_count

            # -----------------------------------------------------------------
            # LIVE MACRO-ECONOMIC STANDING VECTOR CALCULUS
            # -----------------------------------------------------------------
            max_owner_id = max([p[1] for p in normalized_planets] + [0])
            P = 2.0 if max_owner_id <= 1 else 4.0
            
            total_hostile_dist = sum(math.sqrt((t[2]-base_planet[2])**2 + (t[3]-base_planet[3])**2) for t in hostile_planets)
            S = total_hostile_dist / max(1, len(hostile_planets))
            
            # Map structural relative production standing (rho)
            our_total_prod = sum(p[6] for p in normalized_planets if p[1] == player_id)
            enemy_ids = set(p[1] for p in normalized_planets if p[1] != player_id and p[1] != -1)
            max_enemy_prod = max([sum(p[6] for p in normalized_planets if p[1] == e_id) for e_id in enemy_ids]) if enemy_ids else 1
            
            rho = our_total_prod / max(1, max_enemy_prod)

            w_dis = max(0.10, min(2.00, self.alpha_dis * math.exp(self.beta_dis * S)))
            w_gr  = max(0.05, min(2.50, self.alpha_gr / max(0.05, rho)))
            w_ns  = max(0.05, min(2.50, (self.alpha_ns * P) / max(0.05, rho)))
            pool_perc = max(0.45, min(0.98, self.gamma_pool - (self.alpha_pool * (P - 2.0)) + (self.beta_pool * rho)))

            # -----------------------------------------------------------------
            # TIME-HORIZON INBOUND MATRIX GENERATION
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
                    if f_target not in friendly_inbound_matrix: friendly_inbound_matrix[f_target] = []
                    friendly_inbound_matrix[f_target].append((f_ships, f_turns))
                else:
                    if f_target not in hostile_inbound_matrix: hostile_inbound_matrix[f_target] = []
                    hostile_inbound_matrix[f_target].append((f_ships, f_turns))

            # =====================================================================
            # TWIN-QUEUE MPC SIMULATOR ROUTINE (STRATEGIC VS. TEMPORAL ACCELERATION)
            # =====================================================================
            ais_queue = []
            easy_queue = []
            
            base_buffer = base_planet[5] - 10
            test_launch_mass = max(15, int(base_buffer * pool_perc)) if base_buffer > 0 else 15
            
            for target in hostile_planets:
                if target[2] == 0.0 and target[3] == 0.0: continue
                if target[0] in self.virtual_blacklist: continue 
                
                if is_early_game and target[0] in friendly_inbound_matrix:
                    total_friendly_en_route = sum(ships for ships, _ in friendly_inbound_matrix[target[0]])
                    max_flight_horizon = max(turns for _, turns in friendly_inbound_matrix[target[0]])
                    simulated_defense = target[5]
                    if target[1] != -1: simulated_defense += target[6] * max_flight_horizon
                    if target[0] in hostile_inbound_matrix:
                        for h_ships, h_turns in hostile_inbound_matrix[target[0]]:
                            if h_turns <= max_flight_horizon: simulated_defense += h_ships
                    if total_friendly_en_route > simulated_defense: continue
                
                intercept_data = calculate_exact_ballistic_angle(base_planet, target, test_launch_mass, game_angular_velocity, obs)
                if intercept_data[0] is not None:
                    angle, f_time = intercept_data
                    
                    dx_future = target[2] - base_planet[2]
                    dy_future = target[3] - base_planet[3]
                    dist_future = max(0.1, math.sqrt(dx_future * dx_future + dy_future * dy_future) - base_planet[4])
                    
                    predicted_enemy_garrison = target[5]
                    if target[1] != -1: predicted_enemy_garrison += target[6] * (math.ceil(f_time) + 1)
                    
                    # Target populates Temporal Easy Queue if fully defeatable
                    if test_launch_mass > predicted_enemy_garrison:
                        easy_queue.append((f_time, target))
                    
                    # Target populates Strategic AIS Queue
                    score = ((target[6] * w_gr) + 1.0) / ((predicted_enemy_garrison * w_ns) + (dist_future * w_dis) + 1.0)
                    ais_queue.append((score, target))
                    
            ais_queue.sort(key=lambda x: x[0], reverse=True)
            easy_queue.sort(key=lambda x: x[0])
            
            if not ais_queue: return []
            
            # Extract top branching nodes
            ais_1 = ais_queue[0][1]
            ais_2 = ais_queue[1][1] if len(ais_queue) > 1 else ais_1
            easy_1 = easy_queue[0][1] if easy_queue else ais_1
            
            best_target_planet = None
            
            # -----------------------------------------------------------------
            # SCENARIO 3: THE SHORT-CIRCUIT GATING LOGIC
            # -----------------------------------------------------------------
            if ais_1[0] == easy_1[0]:
                best_target_planet = ais_1
            else:
                # -----------------------------------------------------------------
                # FORWARD TIMELINE PROJECTION MATRIX
                # -----------------------------------------------------------------
                horizon = 60.0
                
                # --- TIMELINE A: DIRECT EXPANSION (AIS_1 -> AIS_2) ---
                _, t_a1 = calculate_exact_ballistic_angle(base_planet, ais_1, test_launch_mass, game_angular_velocity, obs)
                remaining_mass_a = max(5, test_launch_mass - ais_1[5])
                _, t_a2 = calculate_exact_ballistic_angle(ais_1, ais_2, remaining_mass_a, game_angular_velocity, obs)
                
                yield_a = 0.0
                for step in range(int(horizon)):
                    if step < t_a1:
                        yield_a += our_total_prod
                    elif step < (t_a1 + t_a2):
                        yield_a += (our_total_prod + ais_1[6])
                    else:
                        yield_a += (our_total_prod + ais_1[6] + ais_2[6])
                        
                # --- TIMELINE B: STEPPING-STONE OUTPOST ROUTE (EASY_1 -> AIS_1) ---
                _, t_b1 = calculate_exact_ballistic_angle(base_planet, easy_1, test_launch_mass, game_angular_velocity, obs)
                remaining_mass_b = max(5, test_launch_mass - easy_1[5])
                _, t_b2 = calculate_exact_ballistic_angle(easy_1, ais_1, remaining_mass_b, game_angular_velocity, obs)
                
                yield_b = 0.0
                for step in range(int(horizon)):
                    if step < t_b1:
                        yield_b += our_total_prod
                    elif step < (t_b1 + t_b2):
                        yield_b += (our_total_prod + easy_1[6])
                    else:
                        yield_b += (our_total_prod + easy_1[6] + ais_1[6])
                        
                # Pick target mapping directly to maximum area under the curve production yield
                if yield_b > yield_a:
                    best_target_planet = easy_1
                else:
                    best_target_planet = ais_1
                    
            if best_target_planet is None: return []
            
            # =====================================================================
            # ACTION LAYER GENERATION & DEPLOYMENT PROTOCOLS
            # =====================================================================
            moves = []
            if is_early_game:
                _, base_f_time = calculate_exact_ballistic_angle(base_planet, best_target_planet, 15, game_angular_velocity, obs)
                target_owner = best_target_planet[1]
                predicted_enemy_garrison = best_target_planet[5]
                if target_owner != -1: predicted_enemy_garrison += best_target_planet[6] * (math.ceil(base_f_time) + 1)
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
                    if allocated_ships >= final_needed: self.virtual_blacklist.add(best_target_planet[0])
            else:
                for my_p in my_planets:
                    if my_p[5] > 5:
                        launch_ships = int(my_p[5]) if my_p[0] == base_planet[0] else int(my_p[5] * pool_perc)
                        if launch_ships >= 5:
                            angle, flight_time = calculate_exact_ballistic_angle(my_p, best_target_planet, launch_ships, game_angular_velocity, obs)
                            if angle is not None:
                                target_owner, target_current_ships, target_production = best_target_planet[1], best_target_planet[5], best_target_planet[6]
                                predicted_enemy_garrison = target_current_ships
                                if target_owner != -1: predicted_enemy_garrison += target_production * (math.ceil(flight_time) + 1)
                                if launch_ships > (predicted_enemy_garrison):
                                    moves.append([int(my_p[0]), float(angle), int(launch_ships)])
                                    my_p[5] -= launch_ships
                                    self.virtual_blacklist.add(best_target_planet[0])
            return moves
        except Exception:
            return []


# ============================================================================
# BOT 2 DEFINITION: CONTINUOUS PARAMETRIC AGENT (BETA VARIANT)
# ============================================================================
class ContinuousAgentBeta:
    def __init__(self):
        self.alpha_dis = 0.3929
        self.beta_dis = 0.0224
        self.alpha_gr = 1.5626
        self.alpha_ns = 0.029
        self.gamma_pool = 0.8429
        self.alpha_pool = 0.0934
        self.beta_pool = 0.2459
        self.last_my_planet_count = -1
        self.virtual_blacklist = set()

    def execute_macro_turn(self, obs):
        try:
            player_id = safe_get(obs, "player", 0)
            current_turn = safe_get(obs, "step", 0)
            game_angular_velocity = safe_get(obs, "angular_velocity", 0.035)
            
            if current_turn == 0:
                self.last_my_planet_count = -1
                self.virtual_blacklist.clear()

            raw_planets = safe_get(obs, "planets", [])
            normalized_planets = normalize_planets(raw_planets)
            my_planets = [p for p in normalized_planets if p[1] == player_id]
            hostile_planets = [p for p in normalized_planets if p[1] != player_id]
            if not my_planets or not hostile_planets: return []
                
            base_planet = max(my_planets, key=lambda x: x[5])
            is_early_game = len(my_planets) < 4

            current_my_planet_count = len(my_planets)
            if current_my_planet_count != self.last_my_planet_count:
                self.virtual_blacklist.clear()
                self.last_my_planet_count = current_my_planet_count

            max_owner_id = max([p[1] for p in normalized_planets] + [0])
            P = 2.0 if max_owner_id <= 1 else 4.0
            total_hostile_dist = sum(math.sqrt((t[2]-base_planet[2])**2 + (t[3]-base_planet[3])**2) for t in hostile_planets)
            S = total_hostile_dist / max(1, len(hostile_planets))
            total_planets = len(normalized_planets)
            neutral_nodes = sum(1 for p in normalized_planets if p[1] == -1)
            phi = neutral_nodes / max(1, total_planets)

            w_dis = max(0.10, min(2.00, self.alpha_dis * math.exp(self.beta_dis * S)))
            w_gr  = max(0.05, min(1.50, self.alpha_gr * (phi / math.sqrt(P))))
            w_ns  = max(0.05, min(1.50, self.alpha_ns * P * ((1.0 - phi) ** 2) + 0.05))
            pool_perc = max(0.45, min(0.98, self.gamma_pool - (self.alpha_pool * (P - 2.0) + self.beta_pool * (1.0 - phi))))

            friendly_inbound_matrix = {}
            hostile_inbound_matrix = {}
            raw_fleets = safe_get(obs, "fleets", [])
            
            for f in raw_fleets:
                f_owner, f_target, f_ships = safe_get(f, "owner"), safe_get(f, "target"), safe_get(f, "ships", 0)
                f_turns = safe_get(f, "turns_left", 0)
                if f_owner == player_id:
                    if f_target not in friendly_inbound_matrix: friendly_inbound_matrix[f_target] = []
                    friendly_inbound_matrix[f_target].append((f_ships, f_turns))
                else:
                    if f_target not in hostile_inbound_matrix: hostile_inbound_matrix[f_target] = []
                    hostile_inbound_matrix[f_target].append((f_ships, f_turns))

            # =====================================================================
            # SURGICAL INJECTION: STEPPING-STONE PROXY TARGET SCANNING CORE
            # =====================================================================
            best_target_planet = None
            best_ais_score = -float('inf')
            base_buffer = base_planet[5] - 10
            test_launch_mass = max(15, int(base_buffer * pool_perc)) if base_buffer > 0 else 15
            comet_ids = set(safe_get(obs, "comet_planet_ids", []))
            
            # Step A: Identify high-yield enemy structures currently hidden behind the sun
            blocked_high_value_nodes = []
            for potential_h in hostile_planets:
                if potential_h[6] >= 3: # Isolate only premium goldmines (income >= 3)
                    if check_sun_collision(base_planet[2], base_planet[3], potential_h[2], potential_h[3]):
                        blocked_high_value_nodes.append(potential_h)
            
            # Step B: Scan open targets using forward proxy value propagation
            for target in hostile_planets:
                if target[2] == 0.0 and target[3] == 0.0: continue
                if target[0] in self.virtual_blacklist: continue 
                
                if is_early_game and target[0] in friendly_inbound_matrix:
                    total_friendly_en_route = sum(ships for ships, _ in friendly_inbound_matrix[target[0]])
                    max_flight_horizon = max(turns for _, turns in friendly_inbound_matrix[target[0]])
                    simulated_defense = target[5]
                    if target[1] != -1: simulated_defense += target[6] * max_flight_horizon
                    if target[0] in hostile_inbound_matrix:
                        for h_ships, h_turns in hostile_inbound_matrix[target[0]]:
                            if h_turns <= max_flight_horizon: simulated_defense += h_ships
                    if total_friendly_en_route > simulated_defense: continue
                
                intercept_data = calculate_exact_ballistic_angle(
                    base_planet, target, test_launch_mass, game_angular_velocity, obs
                )
                
                if intercept_data[0] is not None:
                    angle, f_time = intercept_data
                    
                    # Read structural base production values
                    raw_production = target[6]
                    proxy_bonus = 0.0
                    
                    # Calculate if this open node acts as an unblocked path to a blocked jackpot node
                    for blocked_node in blocked_high_value_nodes:
                        if not check_sun_collision(target[2], target[3], blocked_node[2], blocked_node[3]):
                            dist_to_goldmine = math.sqrt((blocked_node[2]-target[2])**2 + (blocked_node[3]-target[3])**2)
                            # Inherit utility value backwards from the blocked system
                            proxy_bonus = max(proxy_bonus, (blocked_node[6] / max(1.0, dist_to_goldmine)) * 0.50)
                    
                    # Propagated utility value replaces strict flat production metrics
                    effective_production = raw_production + proxy_bonus
                    
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
                    
                    # AIS Evaluation execution pass using updated effective utility metrics
                    score = ((effective_production * w_gr) + 1.0) / ((predicted_enemy_garrison * w_ns) + (dist_future * w_dis) + 1.0)
                    
                    if score > best_ais_score:
                        best_ais_score = score
                        best_target_planet = target
                        
            if best_target_planet is None: return []
            
            # =====================================================================
            # FLEET DISPATCH PROTOCOL LAYER
            # =====================================================================
            moves = []
            if is_early_game:
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
                        self.virtual_blacklist.add(best_target_planet[0])
            else:
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
                                    self.virtual_blacklist.add(best_target_planet[0])
            return moves
        except Exception:
            return []

# ============================================================================
# BOT 3 DEFINITION: CONTINUOUS PARAMETRIC AGENT (CHARLIE VARIANT)
# ============================================================================
class ContinuousAgentCharlie:
    def __init__(self): 
        # =====================================================================
        # PASTE YOUR OPTUNA TUNING RESULTS HERE
        # =====================================================================
        self.alpha_dis = 0.4518
        self.beta_dis = 0.0213
        self.alpha_gr = 0.7601
        self.alpha_ns = 0.1857
        self.gamma_pool = 0.5673
        self.alpha_pool = 0.1933
        self.beta_pool = 0.1054
        # =====================================================================
        
        self.last_my_planet_count = -1
        self.virtual_blacklist = set()

    def execute_macro_turn(self, obs):
        try:
            player_id = safe_get(obs, "player", 0)
            current_turn = safe_get(obs, "step", 0)
            game_angular_velocity = safe_get(obs, "angular_velocity", 0.035)
            
            if current_turn == 0:
                self.last_my_planet_count = -1
                self.virtual_blacklist.clear()

            raw_planets = safe_get(obs, "planets", [])
            normalized_planets = normalize_planets(raw_planets)
            my_planets = [p for p in normalized_planets if p[1] == player_id]
            hostile_planets = [p for p in normalized_planets if p[1] != player_id]
            if not my_planets or not hostile_planets: return []
                
            base_planet = max(my_planets, key=lambda x: x[5])
            is_early_game = len(my_planets) < 4

            current_my_planet_count = len(my_planets)
            if current_my_planet_count != self.last_my_planet_count:
                self.virtual_blacklist.clear()
                self.last_my_planet_count = current_my_planet_count

            # -----------------------------------------------------------------
            # COMPUTE DYNAMIC MACRO DOMINANCE METRICS
            # -----------------------------------------------------------------
            max_owner_id = max([p[1] for p in normalized_planets] + [0])
            P = 2.0 if max_owner_id <= 1 else 4.0
            
            total_hostile_dist = sum(math.sqrt((t[2]-base_planet[2])**2 + (t[3]-base_planet[3])**2) for t in hostile_planets)
            S = total_hostile_dist / max(1, len(hostile_planets))
            
            # Extract relative industrial standing (rho) against highest threat vector
            our_total_prod = sum(p[6] for p in normalized_planets if p[1] == player_id)
            enemy_ids = set(p[1] for p in normalized_planets if p[1] != player_id and p[1] != -1)
            max_enemy_prod = max([sum(p[6] for p in normalized_planets if p[1] == e_id) for e_id in enemy_ids]) if enemy_ids else 1
            
            rho = our_total_prod / max(1, max_enemy_prod)

            # Continuous functional equations processing directly on dominance standing
            w_dis = max(0.10, min(2.00, self.alpha_dis * math.exp(self.beta_dis * S)))
            w_gr  = max(0.05, min(2.50, self.alpha_gr / max(0.05, rho)))
            w_ns  = max(0.05, min(2.50, (self.alpha_ns * P) / max(0.05, rho)))
            pool_perc = max(0.45, min(0.98, self.gamma_pool - (self.alpha_pool * (P - 2.0)) + (self.beta_pool * rho)))

            # -----------------------------------------------------------------
            # TRACK INBOUND BALISTIC ATTACK AND REINFORCEMENT PATHS
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
                    if f_target not in friendly_inbound_matrix: friendly_inbound_matrix[f_target] = []
                    friendly_inbound_matrix[f_target].append((f_ships, f_turns))
                else:
                    if f_target not in hostile_inbound_matrix: hostile_inbound_matrix[f_target] = []
                    hostile_inbound_matrix[f_target].append((f_ships, f_turns))

            best_target_planet = None
            best_ais_score = -float('inf')
            base_buffer = base_planet[5] - 10
            test_launch_mass = max(15, int(base_buffer * pool_perc)) if base_buffer > 0 else 15
            comet_ids = set(safe_get(obs, "comet_planet_ids", []))
            
            # STEPPING-STONE PROXY TARGET SELECTION SCAN
            blocked_high_value_nodes = []
            for potential_h in hostile_planets:
                if potential_h[6] >= 3: 
                    if check_sun_collision(base_planet[2], base_planet[3], potential_h[2], potential_h[3]):
                        blocked_high_value_nodes.append(potential_h)
            
            for target in hostile_planets:
                if target[2] == 0.0 and target[3] == 0.0: continue
                if target[0] in self.virtual_blacklist: continue 
                
                if is_early_game and target[0] in friendly_inbound_matrix:
                    total_friendly_en_route = sum(ships for ships, _ in friendly_inbound_matrix[target[0]])
                    max_flight_horizon = max(turns for _, turns in friendly_inbound_matrix[target[0]])
                    simulated_defense = target[5]
                    if target[1] != -1: simulated_defense += target[6] * max_flight_horizon
                    if target[0] in hostile_inbound_matrix:
                        for h_ships, h_turns in hostile_inbound_matrix[target[0]]:
                            if h_turns <= max_flight_horizon: simulated_defense += h_ships
                    if total_friendly_en_route > simulated_defense: continue
                
                intercept_data = calculate_exact_ballistic_angle(base_planet, target, test_launch_mass, game_angular_velocity, obs)
                if intercept_data[0] is not None:
                    angle, f_time = intercept_data
                    
                    # Forward Proxy Routing Utility calculation
                    raw_production = target[6]
                    proxy_bonus = 0.0
                    for blocked_node in blocked_high_value_nodes:
                        if not check_sun_collision(target[2], target[3], blocked_node[2], blocked_node[3]):
                            dist_to_goldmine = math.sqrt((blocked_node[2]-target[2])**2 + (blocked_node[3]-target[3])**2)
                            proxy_bonus = max(proxy_bonus, (blocked_node[6] / max(1.0, dist_to_goldmine)) * 0.50)
                    
                    effective_production = raw_production + proxy_bonus
                    
                    if target[0] in comet_ids:
                        cx, cy, valid = get_comet_future_pos(obs, target[0], f_time)
                        pred_tx, pred_ty = (cx, cy) if valid else (target[2], target[3])
                    else:
                        dx, dy = target[2] - 50.0, target[3] - 50.0
                        orbital_radius = math.sqrt(dx*dx + dy*dy)
                        future_angle = math.atan2(dy, dx) + (game_angular_velocity * f_time)
                        pred_tx = 50.0 + orbital_radius * math.cos(future_angle)
                        pred_ty = 50.0 + orbital_radius * math.sin(future_angle)
                        
                    dx_future, dy_future = pred_tx - base_planet[2], pred_ty - base_planet[3]
                    dist_future = max(0.1, math.sqrt(dx_future * dx_future + dy_future * dy_future) - base_planet[4])
                    
                    predicted_enemy_garrison = target[5]
                    if target[1] != -1: predicted_enemy_garrison += target[6] * (math.ceil(f_time) + 1)
                    
                    score = ((effective_production * w_gr) + 1.0) / ((predicted_enemy_garrison * w_ns) + (dist_future * w_dis) + 1.0)
                    if score > best_ais_score:
                        best_ais_score = score
                        best_target_planet = target
                        
            if best_target_planet is None: return []
            
            # =====================================================================
            # FLUID DISPATCH PROTOCOL GENERATOR
            # =====================================================================
            moves = []
            if is_early_game:
                _, base_f_time = calculate_exact_ballistic_angle(base_planet, best_target_planet, 15, game_angular_velocity, obs)
                target_owner = best_target_planet[1]
                predicted_enemy_garrison = best_target_planet[5]
                if target_owner != -1: predicted_enemy_garrison += best_target_planet[6] * (math.ceil(base_f_time) + 1)
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
                    if allocated_ships >= final_needed: self.virtual_blacklist.add(best_target_planet[0])
            else:
                for my_p in my_planets:
                    if my_p[5] > 5:
                        launch_ships = int(my_p[5]) if my_p[0] == base_planet[0] else int(my_p[5] * pool_perc)
                        if launch_ships >= 5:
                            angle, flight_time = calculate_exact_ballistic_angle(my_p, best_target_planet, launch_ships, game_angular_velocity, obs)
                            if angle is not None:
                                target_owner, target_current_ships, target_production = best_target_planet[1], best_target_planet[5], best_target_planet[6]
                                predicted_enemy_garrison = target_current_ships
                                if target_owner != -1: predicted_enemy_garrison += target_production * (math.ceil(flight_time) + 1)
                                if launch_ships > (predicted_enemy_garrison):
                                    moves.append([int(my_p[0]), float(angle), int(launch_ships)])
                                    my_p[5] -= launch_ships
                                    self.virtual_blacklist.add(best_target_planet[0])
            return moves
        except Exception:
            return []


# ============================================================================
# BOT 4 DEFINITION: STATIC HEURISTIC MONOLITHIC solo-CARRY BOT
# ============================================================================
class StaticMonolithicAgent:
    def __init__(self):
        self.W_NS = 0.4555           
        self.W_GR = 0.8964           
        self.W_DIS = 0.6578          
        self.POOL_PERC = 0.8730    

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

            friendly_inbound_matrix = {}
            hostile_inbound_matrix = {}
            raw_fleets = safe_get(obs, "fleets", [])
            
            for f in raw_fleets:
                f_owner, f_target, f_ships = safe_get(f, "owner"), safe_get(f, "target"), safe_get(f, "ships", 0)
                f_turns = safe_get(f, "turns_left", 0)
                if f_owner == player_id:
                    if f_target not in friendly_inbound_matrix: friendly_inbound_matrix[f_target] = []
                    friendly_inbound_matrix[f_target].append((f_ships, f_turns))
                else:
                    if f_target not in hostile_inbound_matrix: hostile_inbound_matrix[f_target] = []
                    hostile_inbound_matrix[f_target].append((f_ships, f_turns))

            best_target_planet = None
            best_ais_score = -float('inf')
            base_buffer = base_planet[5] - 10
            test_launch_mass = max(15, int(base_buffer * self.POOL_PERC)) if base_buffer > 0 else 15
            comet_ids = set(safe_get(obs, "comet_planet_ids", []))
            
            for target in hostile_planets:
                if target[2] == 0.0 and target[3] == 0.0: continue
                
                if is_early_game and target[0] in friendly_inbound_matrix:
                    total_friendly_en_route = sum(ships for ships, _ in friendly_inbound_matrix[target[0]])
                    max_flight_horizon = max(turns for _, turns in friendly_inbound_matrix[target[0]])
                    simulated_defense = target[5]
                    if target[1] != -1: simulated_defense += target[6] * max_flight_horizon
                    if target[0] in hostile_inbound_matrix:
                        for h_ships, h_turns in hostile_inbound_matrix[target[0]]:
                            if h_turns <= max_flight_horizon: simulated_defense += h_ships
                    if total_friendly_en_route > simulated_defense: continue
                
                intercept_data = calculate_exact_ballistic_angle(base_planet, target, test_launch_mass, game_angular_velocity, obs)
                if intercept_data[0] is not None:
                    angle, f_time = intercept_data
                    if target[0] in comet_ids:
                        cx, cy, valid = get_comet_future_pos(obs, target[0], f_time)
                        pred_tx, pred_ty = (cx, cy) if valid else (target[2], target[3])
                    else:
                        dx, dy = target[2] - 50.0, target[3] - 50.0
                        orbital_radius = math.sqrt(dx*dx + dy*dy)
                        future_angle = math.atan2(dy, dx) + (game_angular_velocity * f_time)
                        pred_tx = 50.0 + orbital_radius * math.cos(future_angle)
                        pred_ty = 50.0 + orbital_radius * math.sin(future_angle)
                        
                    dx_future, dy_future = pred_tx - base_planet[2], pred_ty - base_planet[3]
                    dist_future = max(0.1, math.sqrt(dx_future * dx_future + dy_future * dy_future) - base_planet[4])
                    predicted_enemy_garrison = target[5]
                    if target[1] != -1: predicted_enemy_garrison += target[6] * math.ceil(f_time)
                    
                    score = ((target[6] * self.W_GR) + 1.0) / ((predicted_enemy_garrison * self.W_NS) + (dist_future * self.W_DIS) + 1.0)
                    if score > best_ais_score:
                        best_ais_score = score
                        best_target_planet = target
                        
            if best_target_planet is None: return []
            
            moves = []
            for my_p in my_planets:
                if is_early_game:
                    garrison_guess = int(best_target_planet[5] + 1)
                    angle, flight_time = calculate_exact_ballistic_angle(my_p, best_target_planet, garrison_guess, game_angular_velocity, obs)
                    if angle is not None:
                        target_owner, target_current_ships, target_production = best_target_planet[1], best_target_planet[5], best_target_planet[6]
                        predicted_enemy_garrison = target_current_ships
                        if target_owner != -1: predicted_enemy_garrison += target_production * math.ceil(flight_time)
                        final_needed = int(predicted_enemy_garrison + 1)
                        if int(my_p[5] - 1) >= final_needed:
                            angle, flight_time = calculate_exact_ballistic_angle(my_p, best_target_planet, final_needed, game_angular_velocity, obs)
                            if angle is not None:
                                moves.append([int(my_p[0]), float(angle), int(final_needed)])
                                my_p[5] -= final_needed
                else:
                    if my_p[5] > 5:
                        available_buffer = my_p[5]
                        launch_ships = int(available_buffer) if my_p[0] == base_planet[0] else int(available_buffer * self.POOL_PERC)
                        if launch_ships >= 5:
                            angle, flight_time = calculate_exact_ballistic_angle(my_p, best_target_planet, launch_ships, game_angular_velocity, obs)
                            if angle is not None:
                                target_owner, target_current_ships, target_production = best_target_planet[1], best_target_planet[5], best_target_planet[6]
                                predicted_enemy_garrison = target_current_ships
                                if target_owner != -1: predicted_enemy_garrison += target_production * math.ceil(flight_time)
                                if launch_ships > (predicted_enemy_garrison):
                                    moves.append([int(my_p[0]), float(angle), int(launch_ships)])
                                    my_p[5] -= launch_ships
            return moves
        except Exception:
            return []


# ============================================================================
# PERSISTENT ENVIRONMENT ROUTER HOOKS (Saves cross-turn process data)
# ============================================================================
BOT_ALPHA_INSTANCES = {}
BOT_BETA_INSTANCES  = {}
BOT_CHARLIE_INSTANCES = {}
STATIC_BOT_INSTANCES = {}

def runner_agent_alpha(obs, config=None):
    p_id = obs.player
    if p_id not in BOT_ALPHA_INSTANCES or obs.step == 0:
        BOT_ALPHA_INSTANCES[p_id] = ContinuousAgentAlpha()
    return BOT_ALPHA_INSTANCES[p_id].execute_macro_turn(obs)

def runner_agent_beta(obs, config=None):
    p_id = obs.player
    if p_id not in BOT_BETA_INSTANCES or obs.step == 0:
        BOT_BETA_INSTANCES[p_id] = ContinuousAgentBeta()
    return BOT_BETA_INSTANCES[p_id].execute_macro_turn(obs)

def runner_agent_charlie(obs, config=None):
    p_id = obs.player
    if p_id not in BOT_CHARLIE_INSTANCES or obs.step == 0:
        BOT_CHARLIE_INSTANCES[p_id] = ContinuousAgentCharlie()
    return BOT_CHARLIE_INSTANCES[p_id].execute_macro_turn(obs)

def runner_agent_static(obs, config=None):
    p_id = obs.player
    if p_id not in STATIC_BOT_INSTANCES or obs.step == 0:
        STATIC_BOT_INSTANCES[p_id] = StaticMonolithicAgent()
    return STATIC_BOT_INSTANCES[p_id].execute_macro_turn(obs)


# =====================================================================
# SYSTEM TOURNAMENT VALIDATION ORCHESTRATOR
# =====================================================================
def run_mega_tournament():
    # Win trackers
    wins_4p = {"Alpha": 0, "Beta": 0, "Static": 0, "Charlie": 0}
    wins_1v1 = {
        "Alpha_vs_Beta": 0, "Beta_vs_Alpha": 0,
        "Alpha_vs_Static": 0, "Static_vs_Alpha": 0,
        "Beta_vs_Static": 0, "Static_vs_Beta": 0,
        "Alpha_vs_Charlie": 0, "Charlie_vs_Alpha": 0,
        "Beta_vs_Charlie": 0, "Charlie_vs_Beta": 0,
        "Charlie_vs_Static": 0, "Static_vs_Charlie": 0
    }

    print(f"Launching Consolidated Battle Matrix ({TOTAL_VALIDATION_MATCHES} Passes Per Bracket)... ⚔️")

    # --- BLOCK 1: 4-PLAYER ROYAL RUMBLE MATCHUP ---
    print("\n--- Bracket I: Starting 4-Player Simultaneous Rumble ---")
    for match in range(TOTAL_VALIDATION_MATCHES):
        env = make("orbit_wars", debug=True)
        steps = env.run([runner_agent_alpha, runner_agent_beta, runner_agent_static, runner_agent_charlie])
        final_planets = normalize_planets(steps[-1][0]['observation']['planets'])
        scores = [0, 0, 0, 0]
        for p in final_planets:
            if p[1] != -1: scores[p[1]] += 1
        
        winner = np.argmax(scores)
        if winner == 0:   wins_4p["Alpha"] += 1; print(f"  Match Rumble-{match+1:02d}: WINNER -> 🔵")
        elif winner == 1: wins_4p["Beta"] += 1;  print(f"  Match Rumble-{match+1:02d}: WINNER -> 🔴")
        elif winner == 2: wins_4p["Static"] += 1; print(f"  Match Rumble-{match+1:02d}: WINNER -> 🟢")
        elif winner == 3: wins_4p["Charlie"] += 1;  print(f"  Match Rumble-{match+1:02d}: WINNER -> 🟡")

    # --- BLOCK 2: 1V1 PAIRING MATRIX DUELS ---
    print("\n--- Bracket II: Head-to-Head Duel Combos ---")
    
    # Pair A: Alpha vs Beta
    for match in range(TOTAL_VALIDATION_MATCHES):
        env = make("orbit_wars", debug=False)
        steps = env.run([runner_agent_alpha, runner_agent_beta])
        final_planets = normalize_planets(steps[-1][0]['observation']['planets'])
        s = [0, 0]
        for p in final_planets:
            if p[1] == 0: s[0] += 1
            elif p[1] == 1: s[1] += 1
        if np.argmax(s) == 0: wins_1v1["Alpha_vs_Beta"] += 1
        else: wins_1v1["Beta_vs_Alpha"] += 1
    print(f"  -> Duel Set [Alpha vs Beta] Completed. Results: Alpha ({wins_1v1['Alpha_vs_Beta']}) | Beta ({wins_1v1['Beta_vs_Alpha']})")

    # Pair B: Alpha vs Static
    for match in range(TOTAL_VALIDATION_MATCHES):
        env = make("orbit_wars", debug=False)
        steps = env.run([runner_agent_alpha, runner_agent_static])
        final_planets = normalize_planets(steps[-1][0]['observation']['planets'])
        s = [0, 0]
        for p in final_planets:
            if p[1] == 0: s[0] += 1
            elif p[1] == 1: s[1] += 1
        if np.argmax(s) == 0: wins_1v1["Alpha_vs_Static"] += 1
        else: wins_1v1["Static_vs_Alpha"] += 1
    print(f"  -> Duel Set [Alpha vs Static] Completed. Results: Alpha ({wins_1v1['Alpha_vs_Static']}) | Static ({wins_1v1['Static_vs_Alpha']})")

    # Pair C: Beta vs Static
    for match in range(TOTAL_VALIDATION_MATCHES):
        env = make("orbit_wars", debug=False)
        steps = env.run([runner_agent_beta, runner_agent_static])
        final_planets = normalize_planets(steps[-1][0]['observation']['planets'])
        s = [0, 0]
        for p in final_planets:
            if p[1] == 0: s[0] += 1
            elif p[1] == 1: s[1] += 1
        if np.argmax(s) == 0: wins_1v1["Beta_vs_Static"] += 1
        else: wins_1v1["Static_vs_Beta"] += 1
    print(f"  -> Duel Set [Beta vs Static] Completed. Results: Beta ({wins_1v1['Beta_vs_Static']}) | Static ({wins_1v1['Static_vs_Beta']})")

    # Pair D: Alpha vs Charlie
    for match in range(TOTAL_VALIDATION_MATCHES):
        env = make("orbit_wars", debug=False)
        steps = env.run([runner_agent_alpha, runner_agent_charlie])
        final_planets = normalize_planets(steps[-1][0]['observation']['planets'])
        s = [0, 0]
        for p in final_planets:
            if p[1] == 0: s[0] += 1
            elif p[1] == 1: s[1] += 1
        if np.argmax(s) == 0: wins_1v1["Alpha_vs_Charlie"] += 1
        else: wins_1v1["Charlie_vs_Alpha"] += 1
    print(f"  -> Duel Set [Alpha vs Charlie] Completed. Results: Alpha ({wins_1v1['Alpha_vs_Charlie']}) | Charlie ({wins_1v1['Charlie_vs_Alpha']})")

    # Pair E: Beta vs Charlie
    for match in range(TOTAL_VALIDATION_MATCHES):
        env = make("orbit_wars", debug=False)
        steps = env.run([runner_agent_beta, runner_agent_charlie])
        final_planets = normalize_planets(steps[-1][0]['observation']['planets'])
        s = [0, 0]
        for p in final_planets:
            if p[1] == 0: s[0] += 1
            elif p[1] == 1: s[1] += 1
        if np.argmax(s) == 0: wins_1v1["Beta_vs_Charlie"] += 1
        else: wins_1v1["Charlie_vs_Beta"] += 1
    print(f"  -> Duel Set [Beta vs Charlie] Completed. Results: Beta ({wins_1v1['Beta_vs_Charlie']}) | Charlie ({wins_1v1['Charlie_vs_Beta']})")

    # Pair F: Charlie vs Static
    for match in range(TOTAL_VALIDATION_MATCHES):
        env = make("orbit_wars", debug=False)
        steps = env.run([runner_agent_charlie, runner_agent_static])
        final_planets = normalize_planets(steps[-1][0]['observation']['planets'])
        s = [0, 0]
        for p in final_planets:
            if p[1] == 0: s[0] += 1
            elif p[1] == 1: s[1] += 1
        if np.argmax(s) == 0: wins_1v1["Charlie_vs_Static"] += 1
        else: wins_1v1["Static_vs_Charlie"] += 1
    print(f"  -> Duel Set [Charlie vs Static] Completed. Results: Charlie ({wins_1v1['Charlie_vs_Static']}) | Static ({wins_1v1['Static_vs_Charlie']})")

    # --- REPORT TERMINAL SUMMARY METRICS ---
    print("\n" + "="*75)
    print("🏆 FINAL ARENA TOURNAMENT BENCHMARK REPORT")
    print("="*75)
    print(" [4-PLAYER RUMBLE DOMINANCE SHARE]")
    print(f"    Agent Alpha:       {(wins_4p['Alpha']/TOTAL_VALIDATION_MATCHES)*100:.1f}% ({wins_4p['Alpha']}/{TOTAL_VALIDATION_MATCHES})")
    print(f"    Agent Beta:        {(wins_4p['Beta']/TOTAL_VALIDATION_MATCHES)*100:.1f}% ({wins_4p['Beta']}/{TOTAL_VALIDATION_MATCHES})")
    print(f"    Static Monolithic: {(wins_4p['Static']/TOTAL_VALIDATION_MATCHES)*100:.1f}% ({wins_4p['Static']}/{TOTAL_VALIDATION_MATCHES})")
    print(f"    Agent Charlie:     {(wins_4p['Charlie']/TOTAL_VALIDATION_MATCHES)*100:.1f}% ({wins_4p['Charlie']}/{TOTAL_VALIDATION_MATCHES})")
    print("-"*75)
    print(" [1V1 DUEL WIN RATES]")
    print(f"    Alpha vs Beta:     {(wins_1v1['Alpha_vs_Beta']/TOTAL_VALIDATION_MATCHES)*100:.1f}% Win Rate for Alpha")
    print(f"    Alpha vs Static:   {(wins_1v1['Alpha_vs_Static']/TOTAL_VALIDATION_MATCHES)*100:.1f}% Win Rate for Alpha")
    print(f"    Beta vs Static:    {(wins_1v1['Beta_vs_Static']/TOTAL_VALIDATION_MATCHES)*100:.1f}% Win Rate for Beta")
    print(f"    Alpha vs Charlie:  {(wins_1v1['Alpha_vs_Charlie']/TOTAL_VALIDATION_MATCHES)*100:.1f}% Win Rate for Alpha")
    print(f"    Beta vs Charlie:   {(wins_1v1['Beta_vs_Charlie']/TOTAL_VALIDATION_MATCHES)*100:.1f}% Win Rate for Beta")
    print(f"    Charlie vs Static: {(wins_1v1['Charlie_vs_Static']/TOTAL_VALIDATION_MATCHES)*100:.1f}% Win Rate for Charlie")
    print("="*75)

if __name__ == "__main__":
    run_mega_tournament()