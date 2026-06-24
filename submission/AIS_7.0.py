import math

# =====================================================================
# GLOBAL COHESIVE RELATIVE KINEMATICS ENGINE (COMET-AWARE INTERCEPT)
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
# MASTER TWIN-QUEUE MPC DECENTRALIZED HYPER-GROWTH SUBMISSION AGENT
# ============================================================================
class KaggleAISBallisticSubmissionAgent:
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
# KAGGLE ENVIRONMENTS PLATFORM RUNTIME HOOK
# ============================================================================
GLOBAL_SUBMISSION_CONTEXT = None

def agent(obs, config=None):
    global GLOBAL_SUBMISSION_CONTEXT
    if GLOBAL_SUBMISSION_CONTEXT is None:
        GLOBAL_SUBMISSION_CONTEXT = KaggleAISBallisticSubmissionAgent()
    return GLOBAL_SUBMISSION_CONTEXT.execute_macro_turn(obs)