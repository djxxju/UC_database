import unittest
import json
from pathlib import Path
from uc_model import build_model, interpolate_cost

class ModelTests(unittest.TestCase):
    def test_compact_formulation_fits_limited_license(self):
        from solve_compare import DEFAULT_INPUT
        raw=DEFAULT_INPUT
        m=build_model(json.loads(raw.read_text(encoding='utf-8')))
        self.assertLessEqual(len(m['variables']),2000)
        self.assertLessEqual(len(m['rows']),2000)
        self.assertEqual(len(m['derived_variables']),480)
    def test_interpolation_and_breakpoint(self):
        self.assertAlmostEqual(interpolate_cost([10, 50, 100], [100, 500, 1500], 30),300)
        self.assertEqual(interpolate_cost([10, 50, 100], [100, 500, 1500], 50),500)
        with self.assertRaises(ValueError):interpolate_cost([10,50],[100,500],0)

    def test_initial_residual_off_obligation(self):
        g={'Bus':'b1','Production cost curve (MW)':[10,100],'Production cost curve ($)':[100,1000], 'Initial status (h)':-1,'Initial power (MW)':0,'Minimum uptime (h)':4,'Minimum downtime (h)':3,'Ramp up limit (MW)':50,'Ramp down limit (MW)':50,'Startup costs ($)':[10],'Startup delays (h)':[3],'Reserve eligibility':['r1']}
        d={'Parameters':{'Time (h)':4,'Version':'0.3'},'Generators':{'g0':g},'Buses':{'b1':{'Load (MW)':[0,0,10,10]}},'Reserves':{'r1':{'Type':'Spinning','Amount (MW)':[0]*4}}}
        m=build_model(d)
        self.assertEqual(m['variables']['u_g0_1']['ub'],0)
        self.assertEqual(m['variables']['u_g0_2']['ub'],0)
        self.assertEqual(m['variables']['u_g0_3']['ub'],1)
        g['Startup limit (MW)']=12
        with self.assertRaises(ValueError):build_model(d)

if __name__=='__main__':unittest.main()
