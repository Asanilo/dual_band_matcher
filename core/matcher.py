import numpy as np
import cmath

class DualBandMatchingDesign:
    def __init__(self, f1, f2, Z_L1, Z_L2, Z0=50.0):
        """
        Initialize Dual Band Matching Design
        :param f1: Frequency 1 (Hz)
        :param f2: Frequency 2 (Hz), f2 > f1
        :param Z_L1: Load Impedance at f1 (Complex)
        :param Z_L2: Load Impedance at f2 (Complex)
        :param Z0: System Characteristic Impedance (Ohm)
        """
        self.f1 = f1
        self.f2 = f2
        self.Z_L1_orig = Z_L1
        self.Z_L2_orig = Z_L2
        self.Z_L1 = Z_L1
        self.Z_L2 = Z_L2
        self.Z0 = Z0
        
        # Frequency ratio factors
        self.p1 = f1 / (f1 + f2)
        self.p2 = f2 / (f1 + f2)
        
        # State variables
        self.aux_line_Z = None
        self.aux_line_theta = None
        self.Z1 = None
        self.theta1 = None
        self.region = None
        self.aux_stub_type = None
        self.aux_stub_Y2 = None
        self.Z_T1 = None
        self.theta_T1 = None
        self.Z_m = None
        self.stub_type = None
        self.Z_n = None
        self.Y_n = None

    def apply_aux_line(self, Z_p, theta_deg):
        """
        Apply auxiliary transmission line transformation
        :param Z_p: Characteristic impedance of aux line
        :param theta_deg: Electrical length in degrees (at f1+f2)
        """
        theta_rad = np.radians(theta_deg)
        theta_p1 = theta_rad * self.p1
        theta_p2 = theta_rad * self.p2
        
        # Transmission line transformation
        # Z_in = Z0 * (ZL + j Z0 tan(theta)) / (Z0 + j ZL tan(theta))
        num1 = self.Z_L1_orig + 1j * Z_p * np.tan(theta_p1)
        den1 = Z_p + 1j * self.Z_L1_orig * np.tan(theta_p1)
        Z_L1_new = Z_p * num1 / den1
        
        num2 = self.Z_L2_orig + 1j * Z_p * np.tan(theta_p2)
        den2 = Z_p + 1j * self.Z_L2_orig * np.tan(theta_p2)
        Z_L2_new = Z_p * num2 / den2
        
        self.Z_L1 = Z_L1_new
        self.Z_L2 = Z_L2_new
        self.aux_line_Z = Z_p
        self.aux_line_theta = theta_rad

    def calculate_conjugate_transform(self, additional_pi=0):
        """
        Stage 1: Calculate Conjugate Transform TL1
        """
        R_L1, X_L1 = self.Z_L1.real, self.Z_L1.imag
        R_L2, X_L2 = self.Z_L2.real, self.Z_L2.imag
        
        if abs(R_L2 - R_L1) < 1e-6:
            return False
            
        term1 = R_L1 * R_L2 + X_L1 * X_L2
        term2 = (X_L1 + X_L2) / (R_L2 - R_L1) * (R_L1 * X_L2 - R_L2 * X_L1)
        inside_sqrt = term1 + term2
        
        if inside_sqrt < 0:
            return False 
            
        self.Z1 = np.sqrt(inside_sqrt)
        
        numerator = self.Z1 * (R_L2 - R_L1)
        denominator = R_L2 * X_L1 - R_L1 * X_L2
        
        # Avoid division by zero
        if abs(denominator) < 1e-9:
            theta1_rad = np.pi / 2
        else:
            theta1_rad = np.arctan(numerator / denominator)
        
        if theta1_rad < 0:
            theta1_rad += np.pi
            
        self.theta1 = theta1_rad + additional_pi * np.pi
        
        # Calculate Z_in1 for next stage
        theta1_f1 = self.theta1 * self.p1
        self.Z_in1 = self.Z1 * (self.Z_L1 + 1j * self.Z1 * np.tan(theta1_f1)) / (self.Z1 + 1j * self.Z_L1 * np.tan(theta1_f1))
        
        return True

    def check_region_and_adjust(self, allow_aux_stub=True):
        """
        Stage 2: Check Smith Chart region and add aux stub if needed (Case c)
        """
        z_norm = self.Z_in1 / self.Z0
        r = z_norm.real
        g = (1/z_norm).real
        
        self.Z_in_matched = self.Z_in1
        
        if r > 1:
            self.region = 'a'
        elif g > 1:
            self.region = 'b'
        else:
            self.region = 'c'
            if allow_aux_stub:
                self._add_auxiliary_stub()
            
    def _add_auxiliary_stub(self):
        """
        Handle Case [c] by adding parallel auxiliary stub
        """
        Y_in1 = 1.0 / self.Z_in1
        G_in1 = Y_in1.real
        B_in1 = Y_in1.imag
        
        # Target B_stub = -B_in1 to make Z_in real
        target_B_stub = -B_in1
        theta_stub_f1 = self.p1 * np.pi
        tan_theta = np.tan(theta_stub_f1)
        
        # Try Open Stub
        Y2_open = target_B_stub / tan_theta if abs(tan_theta) > 1e-9 else 0
        
        # Try Short Stub
        Y2_short = -target_B_stub * tan_theta
        
        if Y2_open > 0:
            self.aux_stub_type = 'Open'
            self.aux_stub_Y2 = Y2_open
            Y_stub = 1j * Y2_open * tan_theta
        elif Y2_short > 0:
            self.aux_stub_type = 'Short'
            self.aux_stub_Y2 = Y2_short
            Y_stub = -1j * Y2_short / tan_theta
        else:
            # Fallback or failure
            self.aux_stub_type = 'Open' 
            self.aux_stub_Y2 = 0.02 # Dummy
            Y_stub = 0

        Y_in_new = Y_in1 + Y_stub
        self.Z_in_matched = 1.0 / Y_in_new
        self.region = 'a' # Forced to a

    def calculate_matching_network(self):
        """
        Stage 3: Calculate Pi-network parameters
        """
        R_in1 = self.Z_in_matched.real
        X_in1 = self.Z_in_matched.imag
        Z_S = self.Z0
        
        term_sqrt = (X_in1**2 * Z_S) / (R_in1 - Z_S) + R_in1 * Z_S
        
        if term_sqrt < 0:
            return False
            
        self.Z_T1 = np.sqrt(term_sqrt)
        
        num = self.Z_T1 * (Z_S - R_in1)
        den = X_in1 * Z_S
        
        if abs(den) < 1e-9:
             theta_T1_rad = np.pi/2
        else:
             theta_T1_rad = np.arctan(num / den)
        
        if theta_T1_rad <= 0:
            theta_T1_rad += np.pi
            
        self.theta_T1 = theta_T1_rad
        return True

    def synthesize_pi_network(self):
        """
        Stage 4: Synthesize Pi-network components
        """
        theta_m1 = self.p1 * np.pi
        self.Z_m = (self.Z_T1 * np.sin(self.theta_T1)) / np.sin(theta_m1)
        
        theta_n1 = self.p1 * np.pi
        B_n1 = (np.cos(theta_n1) - np.cos(self.theta_T1)) / (self.Z_m * np.sin(theta_n1))
        
        tan_theta = np.tan(theta_n1)
        
        Y_open = B_n1 / tan_theta if abs(tan_theta) > 1e-9 else 0
        Y_short = -B_n1 * tan_theta
        
        if Y_open > 0:
            self.stub_type = "Open"
            self.Y_n = Y_open
        elif Y_short > 0:
            self.stub_type = "Short"
            self.Y_n = Y_short
        else:
            # Default to Open if both fail (should not happen in theory if region is correct)
            self.stub_type = "Open"
            self.Y_n = Y_open if Y_open != 0 else 0.02
            
        self.Z_n = 1.0 / self.Y_n

    def get_design_parameters(self):
        """
        Return a dictionary of the design parameters
        """
        f_design = self.f1 + self.f2
        
        params = {
            "f_design": f_design,
            "region": self.region,
            "Z_aux": self.aux_line_Z if self.aux_line_Z else 0,
            "theta_aux": np.degrees(self.aux_line_theta) if self.aux_line_theta else 0,
            "Z1": self.Z1,
            "theta1": np.degrees(self.theta1),
            "Z_series": self.Z_m,
            "Z_stub": self.Z_n,
            "stub_type": self.stub_type,
            "aux_stub_type": self.aux_stub_type,
            "aux_stub_Z": (1.0/self.aux_stub_Y2) if self.aux_stub_Y2 else 0
        }
        return params

    def verify_metrics(self):
        """
        Calculate VSWR at f1 and f2
        """
        def tline_input_z(z_l, z_c, theta_rad):
            if abs(np.cos(theta_rad)) < 1e-9:
                if abs(z_l) < 1e-9: return complex(1e9, 0)
                return z_c**2 / z_l
            t = 1j * np.tan(theta_rad)
            return z_c * (z_l + z_c * t) / (z_c + z_l * t)

        def stub_admittance(y_c, theta_rad, is_open):
            if abs(np.cos(theta_rad)) < 1e-9:
                return complex(0, 1e9) if is_open else 0
            if abs(np.sin(theta_rad)) < 1e-9:
                return 0 if is_open else complex(0, -1e9)
            if is_open:
                return 1j * y_c * np.tan(theta_rad)
            else:
                return -1j * y_c / np.tan(theta_rad)

        results = {}
        for f, z_l_orig in [(self.f1, self.Z_L1_orig), (self.f2, self.Z_L2_orig)]:
            scale = f / (self.f1 + self.f2)
            
            # 0. Aux Line
            current_z = z_l_orig
            if self.aux_line_Z:
                theta_aux_f = self.aux_line_theta * scale
                current_z = tline_input_z(current_z, self.aux_line_Z, theta_aux_f)
            
            # 1. TL1
            theta1_f = self.theta1 * scale
            current_z = tline_input_z(current_z, self.Z1, theta1_f)
            
            # 2. Aux Stub (Case c)
            if self.aux_stub_type:
                theta_stub = np.pi * scale
                y_stub = stub_admittance(self.aux_stub_Y2, theta_stub, self.aux_stub_type == 'Open')
                current_z = 1.0 / (1.0/current_z + y_stub)
            
            # 3. Pi Network
            theta_pi = np.pi * scale
            y_pi_stub = stub_admittance(self.Y_n, theta_pi, self.stub_type == 'Open')
            
            # Shunt 1
            current_z = 1.0 / (1.0/current_z + y_pi_stub)
            # Series
            current_z = tline_input_z(current_z, self.Z_m, theta_pi)
            # Shunt 2
            current_z = 1.0 / (1.0/current_z + y_pi_stub)
            
            rho = (current_z - self.Z0) / (current_z + self.Z0)
            vswr = (1 + abs(rho)) / (1 - abs(rho))
            results[f] = vswr
            
        return results

def find_all_designs(f1, f2, Z_L1, Z_L2, Z0=50.0, allow_aux_stub=True, scan_load_aux_line=True):
    """
    Exhaustive search for valid designs
    """
    candidates = []
    
    # Search space
    if scan_load_aux_line:
        theta_aux_range = range(0, 180, 5) # Step 5 degrees
    else:
        theta_aux_range = [0]
        
    k_range = [0, 1]
    
    for theta_aux in theta_aux_range:
        for k in k_range:
            design = DualBandMatchingDesign(f1, f2, Z_L1, Z_L2, Z0)
            
            if theta_aux > 0:
                design.apply_aux_line(50.0, theta_aux)
            
            if not design.calculate_conjugate_transform(additional_pi=k):
                continue
                
            design.check_region_and_adjust(allow_aux_stub=allow_aux_stub)
            
            if not design.calculate_matching_network():
                continue
                
            design.synthesize_pi_network()
            
            params = design.get_design_parameters()
            metrics = design.verify_metrics()
            
            # Add metrics to params
            params['VSWR_f1'] = metrics[f1]
            params['VSWR_f2'] = metrics[f2]
            
            candidates.append(params)
            
    return candidates
