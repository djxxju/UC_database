"""Independent domain checks for the source-selected OR-LIB single-bus profile.

Does not import the model builder or inspect its constraint matrix. Values are
tested unrounded for feasibility; rounding is used only to recognize transitions.
"""
import math

def check_solution(data, values, objective, tolerance=1e-5, objective_tolerance=1e-4):
    generators=data['Generators'];buses=data['Buses'];T=data['Parameters']['Time (h)']
    if len(buses)!=1:raise ValueError('Checker supports this single-bus profile only')
    if any(x!=0 for r in data['Reserves'].values() for x in r['Amount (MW)']):
        raise ValueError('Fixed-zero-reserve projection requires zero reserve demand')
    if any(len(g['Startup costs ($)'])!=1 for g in generators.values()):
        raise ValueError('Checker supports one startup-cost tier only')
    violations={};samples=[];max_violation=0.0;counts={}
    def record(family,amount,where,tol=tolerance):
        nonlocal max_violation
        amount=max(0.0,float(amount));max_violation=max(max_violation,amount)
        counts[family]=counts.get(family,0)+1
        if amount>tol:
            violations[family]=max(violations.get(family,0),amount)
            if len(samples)<40:samples.append({'family':family,'where':where,'violation':amount})
    required=[f'{kind}_{g}_{t}' for g in generators for t in range(1,T+1) for kind in ['u','v','w','p','c']]
    required += [f'shed_{b}_{t}' for b in buses for t in range(1,T+1)]
    bad=[n for n in required if n not in values or not isinstance(values[n],(int,float)) or not math.isfinite(values[n])]
    if not isinstance(objective,(int,float)) or not math.isfinite(objective):bad.append('objective')
    if bad:
        return {'passed':False,'recomputed_objective':None,'max_violation':None,'violations':{'candidate_integrity':len(bad)},'samples':bad[:40],'checked_counts':counts}
    production=0.0;startup=0.0;shedding_cost=0.0
    for name,g in generators.items():
        xs=g['Production cost curve (MW)'];ys=g['Production cost curve ($)'];lo,hi=xs[0],xs[-1]
        initial=g['Initial status (h)'];prev_u=1.0 if initial>0 else 0.0
        prev_q=g['Initial power (MW)']-lo*prev_u
        up=int(g['Minimum uptime (h)']);down=int(g['Minimum downtime (h)'])
        residual=max(0,up-initial) if initial>0 else max(0,down+initial)
        for t in range(1,T+1):
            u,v,w,p,c=(values[f'{kind}_{name}_{t}'] for kind in ['u','v','w','p','c'])
            at=f'{name}, hour {t}'
            for kind,x in [('u',u),('v',v),('w',w)]:
                record('binary',max(abs(x-round(x)),-x,x-1),at+' '+kind)
            record('transition',abs(u-prev_u-v+w),at)
            record('exclusive_start_stop',v+w-1,at)
            record('startup_indicator',abs(v-float(round(u)==1 and round(prev_u)==0)),at)
            record('shutdown_indicator',abs(w-float(round(u)==0 and round(prev_u)==1)),at)
            record('capacity',max(lo*u-p,p-hi*u),at)
            record('nonnegative_power',-p,at)
            record('nonnegative_cost',-c,at)
            if t<=residual:record('initial_residual',abs(u-(1.0 if initial>0 else 0.0)),at)
            if v>0.5:
                for k in range(t,min(T+1,t+up)):record('minimum_uptime',1-values[f'u_{name}_{k}'],f'{name}, start {t}, hour {k}')
            if w>0.5:
                for k in range(t,min(T+1,t+down)):record('minimum_downtime',values[f'u_{name}_{k}'],f'{name}, stop {t}, hour {k}')
            q=p-lo*u
            if t>1 or initial>0:
                record('ramp_up',q-prev_q-g['Ramp up limit (MW)'],at)
                record('ramp_down',prev_q-q-g['Ramp down limit (MW)'],at)
            if u>0.5:
                # Slight numerical endpoint errors are tolerated; out-of-range
                # dispatch has already been exposed by the capacity checks.
                power=min(hi,max(lo,p));amount=None
                for left,right,ca,cb in zip(xs,xs[1:],ys,ys[1:]):
                    if left<=power<=right:
                        amount=ca+(cb-ca)*(power-left)/(right-left);break
                if amount is None:raise ValueError('Invalid cost curve')
                production+=amount
                record('production_cost',abs(c-amount),at,objective_tolerance)
            else:
                record('offline_production',abs(p),at)
                record('production_cost',abs(c),at,objective_tolerance)
            startup+=g['Startup costs ($)'][0]*v
            prev_u=u;prev_q=q
    for bus,b in buses.items():
        for t,demand in enumerate(b['Load (MW)'],1):
            shed=values[f'shed_{bus}_{t}']
            supply=sum(values[f'p_{name}_{t}'] for name,g in generators.items() if g['Bus']==bus)
            record('shedding_bounds',max(-shed,shed-demand),f'{bus}, hour {t}')
            record('balance',abs(supply+shed-demand),f'{bus}, hour {t}')
            shedding_cost+=1000*shed
    total=production+startup+shedding_cost
    record('objective',abs(total-objective),'total',objective_tolerance)
    return {'passed':not violations,'recomputed_objective':total,'production_cost':production,'startup_cost':startup,'load_shedding_penalty':shedding_cost,'total_load_shedding_MWh':shedding_cost/1000,'max_violation':max_violation,'violations':violations,'violation_samples':samples,'checked_counts':counts,'feasibility_tolerance':tolerance,'objective_absolute_tolerance':objective_tolerance,'scope':'Independent scalar checks of the documented source-selected profile; not full UC.jl software reproduction.'}
