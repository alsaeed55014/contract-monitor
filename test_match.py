import re

def normalize(text):
    if not text: return ""
    s = str(text).strip().lower()
    s = re.sub(r'[^\w\s\-]', ' ', s, flags=re.UNICODE)
    return ' '.join(s.split()).strip()

def match_job_sim(customer_job, worker_job, tm_terms=[]):
    c_job = str(customer_job).strip()
    w_job = normalize(worker_job)
    if not c_job or not w_job: return True
    
    search_terms = {normalize(c_job)}
    for s in tm_terms:
        search_terms.add(normalize(s))
                
    results = []
    for term in search_terms:
        if not term: continue
        if term in w_job or w_job in term:
            results.append(f"Matched whole: {term} <-> {w_job}")
            return True, results
        parts = re.split(r'[/,،\-–]+', term)
        for p in parts:
            p = p.strip()
            if len(p) > 2 and (p in w_job or w_job in p):
                results.append(f"Matched part: {p} <-> {w_job}")
                return True, results
    return False, results

print("Test 1: ", match_job_sim("منسق زهور", "منسق مبيعات"))
print("Test 2: ", match_job_sim("منسق زهور", "منسق"))
print("Test 3: ", match_job_sim("منسق زهور", "منسقه زهور"))
