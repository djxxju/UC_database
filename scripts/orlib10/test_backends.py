import json,tempfile,unittest
from pathlib import Path
from uc_model import build_model
from solve_compare import solve_backend,DEFAULT_INPUT
from check_solution import check_solution

class BackendTests(unittest.TestCase):
    def test_both_on_known_optimum_and_clipped_end(self):
        d=json.loads(DEFAULT_INPUT.read_text(encoding='utf-8'))
        g=dict(d['Generators']['g0']);g.update({'Production cost curve (MW)':[10,100],'Production cost curve ($)':[100,1000],'Minimum uptime (h)':4,'Minimum downtime (h)':3,'Ramp up limit (MW)':50,'Ramp down limit (MW)':50,'Startup costs ($)':[10],'Startup delays (h)':[3]})
        d={'Parameters':{'Time (h)':4,'Version':'0.3'},'Generators':{'g0':g},'Buses':{'b1':{'Load (MW)':[0,0,10,10]}},'Reserves':{'r1':{'Type':'Spinning','Amount (MW)':[0]*4}}}
        for backend in ['gurobi','copt']:
            with self.subTest(backend=backend),tempfile.TemporaryDirectory(prefix='uc10_test_') as temp:
                meta,sol=solve_backend(build_model(d),backend,Path(temp),30,1e-8)
                self.assertAlmostEqual(meta['objective'],210,places=5)
                self.assertEqual([round(sol[f'u_g0_{t}']) for t in range(1,5)],[0,0,1,1])
                self.assertTrue(check_solution(d,sol,meta['objective'])['passed'])

if __name__=='__main__':unittest.main()
