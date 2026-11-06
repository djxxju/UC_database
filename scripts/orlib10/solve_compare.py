"""Run one identical linear UC model through Gurobi and COPT; no source edits."""
import argparse,csv,gzip,hashlib,json,os,platform,sys,time,traceback
from datetime import datetime,timezone
from pathlib import Path
from uc_model import build_model

HERE=Path(__file__).resolve().parent
DEFAULT_INPUT=HERE.parents[1]/'cases'/'ucjl_orlib_10_0_1_w_native_v1'/'input.json'

def sha(b):return hashlib.sha256(b).hexdigest()
def save(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def solve_backend(spec,backend,folder,seconds,gap):
    # Native solver file APIs on Windows may reject Unicode absolute paths.
    # Python can set a Unicode working directory; native filenames stay ASCII.
    previous=Path.cwd();folder=folder.resolve();os.chdir(folder)
    try:return _solve_backend(spec,backend,folder,seconds,gap)
    finally:os.chdir(previous)

def _solve_backend(spec,backend,folder,seconds,gap):
    if backend=='gurobi':
        import gurobipy as api
        env=api.Env(params={'OutputFlag':0})
        m=api.Model('orlib_10_uc',env=env)
        m.Params.LogToConsole=0;m.Params.LogFile='solver.log';m.Params.OutputFlag=1
        params={'TimeLimit':seconds,'MIPGap':gap,'MIPGapAbs':1e-7,'Threads':1,'Seed':0,'FeasibilityTol':1e-7,'IntFeasTol':1e-7,'OptimalityTol':1e-7}
        for k,v in params.items():m.setParam(k,v)
        typ={'B':api.GRB.BINARY,'C':api.GRB.CONTINUOUS};version='.'.join(map(str,api.gurobi.version()))
    else:
        import coptpy as api
        env=api.Envr();m=env.createModel('orlib_10_uc');m.setLogFile('solver.log')
        params={'TimeLimit':seconds,'RelGap':gap,'AbsGap':1e-7,'Threads':1,'RandSeed':0,'FeasTol':1e-7,'IntTol':1e-7,'DualTol':1e-7,'LogToConsole':0}
        for k,v in params.items():m.setParam(k,v)
        typ={'B':api.COPT.BINARY,'C':api.COPT.CONTINUOUS};version='.'.join(str(getattr(api.COPT,'VERSION_'+v)) for v in ['MAJOR','MINOR','TECHNICAL'])
    vs={n:m.addVar(lb=v['lb'],ub=v['ub'],vtype=typ[v['type']],name=n) for n,v in spec['variables'].items()}
    for row in spec['rows']:
        expr=api.quicksum(c*vs[n] for n,c in row['coefficients'].items())
        constr={'<=':lambda:expr<=row['rhs'],'>=':lambda:expr>=row['rhs'],'=':lambda:expr==row['rhs']}[row['sense']]()
        m.addConstr(constr,name=row['name'])
    m.setObjective(api.quicksum(c*vs[n] for n,c in spec['objective'].items()),api.GRB.MINIMIZE if backend=='gurobi' else api.COPT.MINIMIZE)
    if backend=='gurobi':m.update()
    m.write('model.lp');m.write('model.mps')
    start=time.perf_counter()
    if backend=='gurobi':m.optimize()
    else:m.solve()
    wall=time.perf_counter()-start
    if backend=='gurobi':
        has=m.SolCount>0;status=m.Status;optimal=status==api.GRB.OPTIMAL
        bound=m.ObjBound if m.IsMIP else None
        meta={'solver_version':version,'status_code':status,'status':'optimal_within_declared_tolerances' if optimal else 'other_see_solver_log','has_solution':has,'objective':m.ObjVal if has else None,'best_bound':bound,'relative_gap':m.MIPGap if has else None,'solver_seconds':m.Runtime,'wall_solve_seconds':wall,'nodes':m.NodeCount,'parameters':params}
        values={n:float(v.X) for n,v in vs.items()} if has else None
    else:
        has=bool(m.getAttr('HasSol'));status=m.getAttr('Status');optimal=status==api.COPT.OPTIMAL
        meta={'solver_version':version,'status_code':status,'status':'optimal_within_declared_tolerances' if optimal else 'other_see_solver_log','has_solution':has,'objective':m.getAttr('ObjVal') if has else None,'best_bound':m.getAttr('ObjBound'),'relative_gap':m.getAttr('BestGap') if has else None,'solver_seconds':m.getAttr('SolvingTime'),'wall_solve_seconds':wall,'nodes':m.getAttr('NodeCnt'),'parameters':params}
        values={n:float(v.x) for n,v in vs.items()} if has else None
    if values is not None:
        for n,expr in spec.get('derived_variables',{}).items():values[n]=sum(c*values[k] for k,c in expr.items())
        save(folder/'solution.json',values)
    save(folder/'solve_metadata.json',meta)
    return meta,values

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,default=DEFAULT_INPUT);ap.add_argument('--output',type=Path);ap.add_argument('--solver',choices=['both','gurobi','copt'],default='both');ap.add_argument('--time-limit',type=float,default=600);ap.add_argument('--gap',type=float,default=1e-8);a=ap.parse_args()
    if a.time_limit<=0 or not 0<=a.gap<1:ap.error('invalid time limit or relative gap')
    out=a.output or HERE/'runs'/datetime.now().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True,exist_ok=False)
    b=a.input.read_bytes();raw=gzip.decompress(b) if a.input.suffix=='.gz' else b;d=json.loads(raw)
    spec=build_model(d);save(out/'linear_model.json',spec)
    model_sha=sha(canonical(spec));save(out/'run_manifest.json',{'created_at':datetime.now(timezone.utc).isoformat(),'input_name':a.input.name,'input_raw_sha256':sha(b),'decompressed_sha256':sha(raw),'model_sha256':model_sha,'python':sys.version,'platform':platform.platform(),'processor':platform.processor(),'code_sha256':{p.name:sha(p.read_bytes()) for p in HERE.glob('*.py')},'profile':'orlib10_audited_defaults_uc_v1','model_variables':len(spec['variables']),'binary_variables':sum(v['type']=='B' for v in spec['variables'].values()),'rows':len(spec['rows'])})
    # The validator is a separate implementation, not a residual test of model rows.
    from check_solution import check_solution
    results={};sols={}
    for backend in (['gurobi','copt'] if a.solver=='both' else [a.solver]):
        folder=out/backend;folder.mkdir()
        try:
            meta,sol=solve_backend(spec,backend,folder,a.time_limit,a.gap)
            meta['model_sha256']=model_sha
            if sol is not None:
                verify=check_solution(d,sol,meta['objective']);save(folder/'verification.json',verify);meta['independent_check']=verify['passed'];meta['recomputed_objective']=verify['recomputed_objective'];sols[backend]=sol
                with (folder/'dispatch.csv').open('w',encoding='utf-8-sig',newline='') as f:
                    writer=csv.writer(f);writer.writerow(['generator','hour','on','startup','shutdown','power_MW'])
                    for g in d['Generators']:
                        for t in range(1,d['Parameters']['Time (h)']+1):writer.writerow([g,t]+[sol[f'{k}_{g}_{t}'] for k in ['u','v','w','p']])
            else:meta['independent_check']='not_run_no_candidate'
            save(folder/'solve_metadata.json',meta);results[backend]=meta
        except Exception as ex:
            results[backend]={'status':'error','error_type':type(ex).__name__,'error':str(ex),'model_sha256':model_sha};save(folder/'error.json',results[backend]);(folder/'traceback.txt').write_text(traceback.format_exc(),encoding='utf-8')
    comparison={'solvers':results,'interpretation':'Same coefficients, separate solves. Single-run timings are not a solver benchmark. This is the documented project profile, not author-result reproduction.'}
    if len(sols)==2:
        x,y=(results[k]['objective'] for k in ['gurobi','copt']);comparison.update(objective_absolute_difference=abs(x-y),objective_relative_difference=abs(x-y)/max(1,abs(x),abs(y)),commitment_differences=sum(round(sols['gurobi'][n])!=round(sols['copt'][n]) for n in sols['gurobi'] if n.startswith('u_')),max_dispatch_difference_MW=max(abs(sols['gurobi'][n]-sols['copt'][n]) for n in sols['gurobi'] if n.startswith('p_')))
    save(out/'comparison.json',comparison)
    print(json.dumps({'output':str(out),'solvers':{k:{j:v.get(j) for j in ['status','objective','best_bound','relative_gap','solver_seconds','independent_check','error']} for k,v in results.items()}},ensure_ascii=False))
    return 0 if all(v.get('independent_check') is True for v in results.values()) else 2

if __name__=='__main__':raise SystemExit(main())
