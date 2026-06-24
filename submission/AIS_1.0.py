import math

class KaggleAISBallisticSubmissionAgent:
    def __init__(self):
        # AIS Evolutionary Optimized Coefficients (Derived from Table II)
        self.W_NS = 0.447      
        self.W_GR = 0.323      
        self.W_DIS = 0.124     
        self.POOL_PERC = 0.814 
        
    def safe_get(self, obj, key, default=None):
        if hasattr(obj, key): return getattr(obj, key)
        if isinstance(obj, dict): return obj.get(key, default)
        return default

    def ships_to_speed(self, ships, max_speed=6.0):
        if ships <= 1: return 1.0
        ratio = math.log(ships) / math.log(1000)
        return 1.0 + (max_speed - 1.0) * (max(0.0, ratio) ** 1.5)

    def check_sun_collision(self, sx, sy, tx, ty):
        cx, cy = 50.0, 50.0
        dx, dy = tx - sx, ty - sy
        len_sq = dx * dx + dy * dy
        if len_sq == 0: return False
        t = max(0.0, min(1.0, ((cx - sx) * dx + (cy - sy) * dy) / len_sq))
        dist = math.sqrt((sx + t * dx - cx)**2 + (sy + t * dy - cy)**2)
        return dist <= 11.5  

    def get_planet_future_pos(self, target_id, absolute_turn, game_angular_velocity, initial_planets):
        p_init = next((p for p in initial_planets if p[0] == target_id), None)
        if not p_init: return 50.0, 50.0
        init_x, init_y, radius = p_init[2], p_init[3], p_init[4]
        dx, dy = init_x - 50.0, init_y - 50.0
        orbital_radius = math.sqrt(dx*dx + dy*dy)
        
        if orbital_radius + radius >= 50.0:
            return init_x, init_y
            
        initial_angle = math.atan2(dy, dx)
        future_angle = initial_angle + (game_angular_velocity * absolute_turn)
        return 50.0 + orbital_radius * math.cos(future_angle), 50.0 + orbital_radius * math.sin(future_angle)

    def calculate_exact_ballistic_angle(self, source_planet, target_planet, num_ships, current_turn, game_angular_velocity, initial_planets):
        """Fixes Point 1: Accounts for the source planet's radius to prevent launch vector drifting."""
        sx, sy, s_rad = source_planet[2], source_planet[3], source_planet[4]
        target_id = target_planet[0]
        fleet_speed = self.ships_to_speed(num_ships)
        
        # Estimate target position
        pred_x, pred_y = target_planet[2], target_planet[3]
        
        for _ in range(10):
            distance = math.sqrt((pred_x - sx)**2 + (pred_y - sy)**2)
            # Spawn correction: Fleet covers (distance - s_rad) space from its actual spawn point
            actual_flight_dist = max(0.1, distance - s_rad)
            flight_time = actual_flight_dist / fleet_speed
            
            pred_x, pred_y = self.get_planet_future_pos(target_id, current_turn + flight_time, game_angular_velocity, initial_planets)
            
        if self.check_sun_collision(sx, sy, pred_x, pred_y):
            return None, 0.0
            
        return math.atan2(pred_y - sy, pred_x - sx), flight_time

    def calculate_ais_score(self, base_planet, target_planet):
        dx = target_planet[2] - base_planet[2]
        dy = target_planet[3] - base_planet[3]
        distance = math.sqrt(dx*dx + dy*dy)
        return ((target_planet[6] * self.W_GR) + 1.0) / ((target_planet[5] * self.W_NS) + (distance * self.W_DIS) + 1.0)

    def execute_macro_turn(self, obs):
        player_id = self.safe_get(obs, "player", 0)
        current_turn = self.safe_get(obs, "step", 0)
        game_angular_velocity = self.safe_get(obs, "angular_velocity", 0.035)
        raw_planets = self.safe_get(obs, "planets", [])
        initial_planets = self.safe_get(obs, "initial_planets", [])
        
        my_planets = [p for p in raw_planets if p[1] == player_id]
        hostile_planets = [p for p in raw_planets if p[1] != player_id]
        if not my_planets or not hostile_planets: return []
            
        base_planet = max(my_planets, key=lambda x: x[5])
        best_target_planet = max(hostile_planets, key=lambda p: self.calculate_ais_score(base_planet, p))
        
        moves = []
        
        for my_p in my_planets:
            if my_p[5] > 15:
                available_buffer = my_p[5] - 10
                
                # Dynamic sizing based on role to create size variance (Fixes Point 4)
                if my_p[0] == base_planet[0]:
                    launch_ships = int(available_buffer * self.POOL_PERC)
                else:
                    launch_ships = int(available_buffer * 0.50)
                
                if launch_ships >= 15:
                    # Get angle and estimated flight duration
                    angle, flight_time = self.calculate_exact_ballistic_angle(
                        my_p, best_target_planet, launch_ships, current_turn, game_angular_velocity, initial_planets
                    )
                    
                    if angle is not None:
                        # Fixes Points 2 & 3: Predict future enemy garrison upon arrival
                        target_owner = best_target_planet[1]
                        target_current_ships = best_target_planet[5]
                        target_production = best_target_planet[6]
                        
                        predicted_enemy_garrison = target_current_ships
                        if target_owner != -1: # Only owned planets produce resources over time
                            predicted_enemy_garrison += target_production * math.ceil(flight_time)
                        
                        # Only commit to launch if our fleet size can decisively crush the future garrison
                        if launch_ships > (predicted_enemy_garrison + 3):
                            moves.append([int(my_p[0]), float(angle), int(launch_ships)])
                            my_p[5] -= launch_ships
                        
        return moves

GLOBAL_SUBMISSION_CONTEXT = None
def agent(obs, config=None):
    global GLOBAL_SUBMISSION_CONTEXT
    if GLOBAL_SUBMISSION_CONTEXT is None:
        GLOBAL_SUBMISSION_CONTEXT = KaggleAISBallisticSubmissionAgent()
    return GLOBAL_SUBMISSION_CONTEXT.execute_macro_turn(obs)