"""Solver-neutral MILP for the audited flat-array, single-tier OR-LIB instance.

All default-derived choices are recorded in MODEL.md, not added to source JSON.
"""
import math

PROFILE='orlib_flat_audited_defaults_uc_v1'

def interpolate_cost(xs,ys,p):
    if not xs[0]-1e-7<=p<=xs[-1]+1e-7:raise ValueError('power outside online curve')
    p=min(xs[-1],max(xs[0],p))
    for a,b,x,y in zip(xs,xs[1:],ys,ys[1:]):
        if p<=b:return x+(y-x)*(p-a)/(b-a)
    raise ValueError('invalid curve')

def build_model(data,compact=True):
    gs=data['Generators'];buses=data['Buses'];T=data['Parameters']['Time (h)']
    if set(data)-{'LICENSE','SOURCE','Parameters','Generators','Buses','Reserves'}:raise ValueError('unsupported top-level extensions')
    if set(data['Parameters'])-{'Time (h)','Version'}:raise ValueError('unsupported explicit parameter overrides')
    if data['Parameters']['Version']!='0.3' or not isinstance(T,int) or T<=0:raise ValueError('requires audited source 0.3 hourly format')
    if len(buses)!=1:raise ValueError('single-bus profile only')
    for r in data['Reserves'].values():
        if len(r['Amount (MW)'])!=T or any(x!=0 for x in r['Amount (MW)']):raise ValueError('only zero reserve demand is implemented')
    m={'profile':PROFILE,'variables':{},'objective':{},'rows':[]}
    def var(n,lb,ub,typ='C',cost=0):
        if n in m['variables']:raise ValueError('duplicate variable')
        m['variables'][n]={'lb':lb,'ub':ub,'type':typ}
        if cost:m['objective'][n]=float(cost)
    def row(name,terms,sense,rhs):
        cf={}
        for n,c in terms:cf[n]=cf.get(n,0)+c
        cf={n:float(c) for n,c in cf.items() if c}
        if not all(n in m['variables'] and math.isfinite(c) for n,c in cf.items()) or not math.isfinite(rhs):raise ValueError('invalid row')
        m['rows'].append({'name':name,'coefficients':cf,'sense':sense,'rhs':float(rhs)})
    for g,a in gs.items():
        allowed={'Bus','Production cost curve (MW)','Production cost curve ($)','Initial status (h)','Initial power (MW)','Minimum uptime (h)','Minimum downtime (h)','Reserve eligibility','Startup costs ($)','Startup delays (h)','Ramp up limit (MW)','Ramp down limit (MW)'}
        if set(a)!=allowed:raise ValueError('unsupported generator fields or missing fields')
        xs=a['Production cost curve (MW)'];ys=a['Production cost curve ($)']
        if a['Bus'] not in buses or len(xs)!=len(ys) or len(xs)<2:raise ValueError('invalid generator curve or bus')
        if not all(math.isfinite(x) for x in xs+ys) or any(x<0 for x in xs+ys):raise ValueError('nonnegative finite curve required')
        if any(x>=y for x,y in zip(xs,xs[1:])):raise ValueError('increasing power points required')
        slopes=[(d-c)/(b-a) for a,b,c,d in zip(xs,xs[1:],ys,ys[1:])]
        if any(a>b+1e-9 for a,b in zip(slopes,slopes[1:])):raise ValueError('convex cost required')
        if len(a['Startup costs ($)'])!=1 or len(a['Startup delays (h)'])!=1 or a['Startup delays (h)'][0]!=a['Minimum downtime (h)']:raise ValueError('single startup tier required')
        if not math.isfinite(a['Startup costs ($)'][0]) or a['Startup costs ($)'][0]<0:raise ValueError('invalid startup cost')
        for key in ['Minimum uptime (h)','Minimum downtime (h)']:
            if not isinstance(a[key],int) or a[key]<1:raise ValueError('integer positive minimum times required')
        if not isinstance(a['Initial status (h)'],int) or a['Initial status (h)']==0:raise ValueError('nonzero integer initial duration required')
        p0=a['Initial power (MW)'];initial=a['Initial status (h)'];on=initial>0
        if not (xs[0]<=p0<=xs[-1] if on else p0==0):raise ValueError('initial power inconsistent')
        for key in ['Ramp up limit (MW)','Ramp down limit (MW)']:
            if not math.isfinite(a[key]) or a[key]<0:raise ValueError('invalid ramp')
        remaining=max(0,(a['Minimum uptime (h)'] if on else a['Minimum downtime (h)'])-abs(initial))
        for t in range(1,T+1):
            fixed=(1 if on else 0) if t<=remaining else None
            var(f'u_{g}_{t}',fixed if fixed is not None else 0,fixed if fixed is not None else 1,'B')
            var(f'v_{g}_{t}',0,1,'B',a['Startup costs ($)'][0]);var(f'w_{g}_{t}',0,1,'B')
            var(f'p_{g}_{t}',0,xs[-1]);var(f'c_{g}_{t}',0,max(ys),cost=1)
    for b,a in buses.items():
        if len(a['Load (MW)'])!=T:raise ValueError('load length mismatch')
        for t,load in enumerate(a['Load (MW)'],1):
            if not math.isfinite(load) or load<0:raise ValueError('invalid demand')
            var(f'shed_{b}_{t}',0,load,cost=1000)
    for g,a in gs.items():
        pmin=a['Production cost curve (MW)'][0];pmax=a['Production cost curve (MW)'][-1];on=int(a['Initial status (h)']>0)
        for t in range(1,T+1):
            u,v,w,p,c=[f'{k}_{g}_{t}' for k in ['u','v','w','p','c']]
            trans=[(u,1),(v,-1),(w,1)]
            if t>1:trans.append((f'u_{g}_{t-1}',-1))
            row(f'transition_{g}_{t}',trans,'=',on if t==1 else 0)
            row(f'exclusive_{g}_{t}',[(v,1),(w,1)],'<=',1)
            row(f'pmin_{g}_{t}',[(p,1),(u,-pmin)],'>=',0)
            row(f'pmax_{g}_{t}',[(p,1),(u,-pmax)],'<=',0)
            row(f'minup_{g}_{t}',[(f'v_{g}_{s}',1) for s in range(max(1,t-a['Minimum uptime (h)']+1),t+1)]+[(u,-1)],'<=',0)
            row(f'mindown_{g}_{t}',[(f'w_{g}_{s}',1) for s in range(max(1,t-a['Minimum downtime (h)']+1),t+1)]+[(u,1)],'<=',1)
            q=[(p,1),(u,-pmin)]
            if t>1:
                diff=q+[(f'p_{g}_{t-1}',-1),(f'u_{g}_{t-1}',pmin)]
                row(f'rampup_{g}_{t}',diff,'<=',a['Ramp up limit (MW)'])
                row(f'rampdown_{g}_{t}',[(n,-coef) for n,coef in diff],'<=',a['Ramp down limit (MW)'])
            elif on:
                q0=a['Initial power (MW)']-pmin
                row(f'initial_rampup_{g}',q,'<=',q0+a['Ramp up limit (MW)'])
                row(f'initial_rampdown_{g}',q,'>=',q0-a['Ramp down limit (MW)'])
            xs=a['Production cost curve (MW)'];ys=a['Production cost curve ($)']
            for k,(x0,x1,y0,y1) in enumerate(zip(xs,xs[1:],ys,ys[1:])):
                slope=(y1-y0)/(x1-x0);intercept=y0-slope*x0
                row(f'cost_{g}_{t}_{k}',[(c,1),(p,-slope),(u,-intercept)],'>=',0)
    for b,a in buses.items():
        for t in range(1,T+1):row(f'balance_{b}_{t}',[(f'p_{g}_{t}',1) for g,a0 in gs.items() if a0['Bus']==b]+[(f'shed_{b}_{t}',1)],'=',a['Load (MW)'][t-1])
    return compact_cost_formulation(m,data) if compact else m

def compact_cost_formulation(model,data):
    """Convex curve weights eliminate P/C and 6 inequalities per unit-hour.

    Lambda>=0, sum(lambda)=u, P=sum(X*lambda), C=sum(Y*lambda).
    Convexity ensures the minimum C for a fixed P is exactly the source PWL.
    Nonadjacent convex combinations cannot underprice a convex cost curve.
    """
    derived={};T=data['Parameters']['Time (h)']
    for g,a in data['Generators'].items():
        xs=a['Production cost curve (MW)'];ys=a['Production cost curve ($)']
        for t in range(1,T+1):
            p=f'p_{g}_{t}';c=f'c_{g}_{t}';terms=[]
            derived[p]={};derived[c]={}
            for k,(x,y) in enumerate(zip(xs,ys)):
                n=f'lam_{g}_{t}_{k}';model['variables'][n]={'lb':0,'ub':1,'type':'C'}
                model['objective'][n]=y;derived[p][n]=x;derived[c][n]=y;terms.append(n)
            del model['variables'][p];del model['variables'][c];del model['objective'][c]
            model['rows'].append({'name':f'curve_weights_{g}_{t}','coefficients':{**{n:1 for n in terms},f'u_{g}_{t}':-1},'sense':'=','rhs':0.0})
    rows=[]
    for row in model['rows']:
        if row['name'].startswith(('pmin_','pmax_','cost_')):continue
        cf={}
        for n,c in row['coefficients'].items():
            for target,weight in derived.get(n,{n:1}).items():cf[target]=cf.get(target,0)+c*weight
        rows.append({**row,'coefficients':{n:float(c) for n,c in cf.items() if c}})
    model['rows']=rows;model['derived_variables']=derived;model['formulation']='convex_weights_pwl_exact_at_minimum'
    return model
