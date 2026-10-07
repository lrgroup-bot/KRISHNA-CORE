def calibration_record(*, simulation_id, predicted, actual, metric, notes=None):
    p=float(predicted); a=float(actual)
    return {"simulation_id":simulation_id,"metric":metric,"predicted":p,"actual":a,
            "error":a-p,"absolute_error":abs(a-p),"notes":notes,"status":"observed"}

def simulation_confidence(*, evidence_coverage=0, calibration_score=0, run_agreement=0):
    vals=[max(0,min(1,float(x))) for x in (evidence_coverage,calibration_score,run_agreement)]
    return round(sum(vals)/len(vals),4)

def truth_boundary(result):
    return {**result,"synthetic":True,"decision_evidence_only":True,
            "may_execute":False,"warning":"Simulation output is a hypothesis, not observed reality."}