import copy, unittest
from check_solution import check_solution

def fixture():
    g={'Bus':'b1','Production cost curve (MW)':[10,100], 'Production cost curve ($)':[100,1000], 'Initial status (h)':3,'Initial power (MW)':20,'Minimum uptime (h)':2,'Minimum downtime (h)':3,'Ramp up limit (MW)':100,'Ramp down limit (MW)':100,'Startup costs ($)':[10],'Startup delays (h)':[3],'Reserve eligibility':['r1']}
    d={'Parameters':{'Time (h)':3,'Version':'0.3'},'Generators':{'g0':g},'Buses':{'b1':{'Load (MW)':[20,20,20]}},'Reserves':{'r1':{'Type':'Spinning','Amount (MW)':[0,0,0]}}}
    s={}
    for t in range(1,4):
        for k,v in [('u',1),('v',0),('w',0),('p',20),('c',200)]:s[f'{k}_g0_{t}']=v
        s[f'shed_b1_{t}']=0
    return d,s

class CheckTests(unittest.TestCase):
    def test_valid_candidate(self):
        d,s=fixture();r=check_solution(d,s,600);self.assertTrue(r['passed'],r);self.assertEqual(r['recomputed_objective'],600)
    def test_balance_error(self):
        d,s=fixture();s['shed_b1_2']=1;r=check_solution(d,s,600);self.assertFalse(r['passed']);self.assertIn('balance',r['violations'])
    def test_cost_error(self):
        d,s=fixture();s['c_g0_1']=201;r=check_solution(d,s,600);self.assertIn('production_cost',r['violations'])
    def test_objective_error(self):
        d,s=fixture();r=check_solution(d,s,601);self.assertIn('objective',r['violations'])
    def test_initial_off_obligation(self):
        d,s=fixture();d['Generators']['g0']['Initial status (h)']=-1;d['Generators']['g0']['Initial power (MW)']=0;s['v_g0_1']=1
        r=check_solution(d,s,610);self.assertIn('initial_residual',r['violations'])
    def test_nan_and_missing(self):
        for kind in ['nan','missing']:
            d,s=fixture()
            if kind=='nan':s['p_g0_1']=float('nan')
            else:del s['p_g0_1']
            r=check_solution(d,s,600);self.assertFalse(r['passed']);self.assertIn('candidate_integrity',r['violations'])
    def test_initial_above_min_ramp(self):
        d,s=fixture();d['Generators']['g0']['Ramp up limit (MW)']=5;s['p_g0_1']=30;s['c_g0_1']=300;d['Buses']['b1']['Load (MW)'][0]=30
        r=check_solution(d,s,700);self.assertIn('ramp_up',r['violations'])
    def test_unsupported_nonzero_reserve(self):
        d,s=fixture();d['Reserves']['r1']['Amount (MW)'][0]=1
        with self.assertRaises(ValueError):check_solution(d,s,600)
    def test_terminal_start_truncated(self):
        d,s=fixture();g=d['Generators']['g0'];g['Initial status (h)']=-3;g['Initial power (MW)']=0;g['Minimum uptime (h)']=4;d['Buses']['b1']['Load (MW)']=[0,0,20]
        for t in [1,2]:
            for k in ['u','v','w','p','c']:s[f'{k}_g0_{t}']=0
        s['v_g0_3']=1
        r=check_solution(d,s,210);self.assertTrue(r['passed'],r)
    def test_initial_offline_has_no_first_ramp(self):
        d,s=fixture();g=d['Generators']['g0'];g['Initial status (h)']=-3;g['Initial power (MW)']=0;g['Ramp up limit (MW)']=1
        d['Buses']['b1']['Load (MW)']=[100]*3
        for t in range(1,4):s[f'p_g0_{t}']=100;s[f'c_g0_{t}']=1000
        s['v_g0_1']=1
        r=check_solution(d,s,3010);self.assertTrue(r['passed'],r)
    def test_above_min_shutdown_ramp(self):
        d,s=fixture();d['Generators']['g0']['Ramp down limit (MW)']=10;d['Buses']['b1']['Load (MW)']=[20,0,0]
        for t in [2,3]:
            for k in ['u','v','w','p','c']:s[f'{k}_g0_{t}']=0
        s['w_g0_2']=1
        r=check_solution(d,s,200);self.assertTrue(r['passed'],r)
        d['Generators']['g0']['Ramp down limit (MW)']=5
        r=check_solution(d,s,200);self.assertIn('ramp_down',r['violations'])
    def test_minimum_uptime_violation(self):
        d,s=fixture();g=d['Generators']['g0'];g['Initial status (h)']=-3;g['Initial power (MW)']=0;d['Buses']['b1']['Load (MW)']=[0,20,0]
        for t in [1,3]:
            for k in ['u','v','w','p','c']:s[f'{k}_g0_{t}']=0
        s['v_g0_2']=1;s['w_g0_3']=1
        r=check_solution(d,s,210);self.assertIn('minimum_uptime',r['violations'])

if __name__=='__main__':unittest.main()
