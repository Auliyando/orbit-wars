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
    return None, None, False

def calculate_exact_ballistic_angle(source_planet, target_planet, num_ships, game_angular_velocity, obs):
    sx, sy, s_rad = source_planet[2], source_planet[3], source_planet[4]
    tx, ty, t_radius = target_planet[2], target_planet[3], target_planet[4]
    target_id = target_planet[0]
    fleet_speed = ships_to_speed(num_ships)
    
    comet_ids = set(safe_get(obs, "comet_planet_ids", []))
    is_comet = target_id in comet_ids
    
    dx = tx - 50.0
    dy = ty - 50.0
    orbital_radius = math.sqrt(dx*dx + dy*dy)
    
    if not is_comet and orbital_radius + t_radius >= 50.0:
        if check_sun_collision(sx, sy, tx, ty): return None, 0.0
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
    return math.atan2(pred_y - sy, pred_x - sx), flight_time

def normalize_planets(raw_planets):
    """FIXED: Robust polymorphic parser prevents string key conversion bugs on live servers."""
    normalized = []
    for p in raw_planets:
        if hasattr(p, "id"):
            normalized.append([p.id, p.owner, p.x, p.y, p.radius, p.ships, p.production])
        elif isinstance(p, dict):
            normalized.append([
                p.get("id", 0),
                p.get("owner", 0),
                p.get("x", 0.0),
                p.get("y", 0.0),
                p.get("radius", 1.0),
                p.get("ships", 0),
                p.get("production", 0)
            ])
        else:
            normalized.append(list(p))
    return normalized


# ============================================================================
# MASTER ANTI-DRIFT ARTIFICIAL IMMUNE SYSTEM SUBMISSION ENGINE
# ============================================================================
class KaggleAISBallisticSubmissionAgent:
    def __init__(self):
        # AIS Evolutionary Optimized Coefficients (Derived from Table II)
        self.W_NS = 0.35      
        self.W_GR = 0.222      
        self.W_DIS = 0.612     
        self.POOL_PERC = 0.952 

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
            
            # =====================================================================
            # PREDICTIVE AIS TARGET SELECTION LOOP (COMET-INTEGRATED)
            # =====================================================================
            best_target_planet = None
            best_ais_score = -float('inf')
            
            base_buffer = base_planet[5] 
            test_launch_mass = int(base_buffer) if base_buffer > 0 else 15
            
            comet_ids = set(safe_get(obs, "comet_planet_ids", []))
            
            for target in hostile_planets:
                # Prevent calculating targets with missing telemetry coordinates to stop top-left drift
                if target[2] == 0.0 and target[3] == 0.0: continue
                
                intercept_data = calculate_exact_ballistic_angle(
                    base_planet, target, test_launch_mass, game_angular_velocity, obs
                )
                
                if intercept_data[0] is not None:
                    angle, f_time = intercept_data
                    
                    # Project destination tracking parameters based on target archetype
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
                    
                    # Compute future garrison metrics at arrival time frame
                    predicted_enemy_garrison = target[5]
                    if target[1] != -1: 
                        predicted_enemy_garrison += target[6] * math.ceil(f_time)
                    
                    # Predictive AIS weight heuristic evaluation
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

GLOBAL_SUBMISSION_CONTEXT = None
def agent(obs, config=None):
    global GLOBAL_SUBMISSION_CONTEXT
    if GLOBAL_SUBMISSION_CONTEXT is None:
        GLOBAL_SUBMISSION_CONTEXT = KaggleAISBallisticSubmissionAgent()
    return GLOBAL_SUBMISSION_CONTEXT.execute_macro_turn(obs)