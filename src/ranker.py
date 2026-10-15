"""
Module: src/ranker.py
Handles candidate evaluation against Must-Have and Nice-to-Have requirements,
calculates match scores, filters candidates, and ranks them.
"""

from typing import List, Dict, Any
from src.matcher import evaluate_requirement

def evaluate_candidate_detailed(
    candidate_info: Dict[str, Any],
    must_have_reqs: Dict[str, List[str]],
    nice_to_have_reqs: Dict[str, List[str]],
    cv_text: str = ""
) -> Dict[str, Any]:
    """
    Evaluates candidate against separate Must-Have and Nice-to-Have requirement categories.
    """
    categories = ["skills", "experience", "education", "languages", "certifications"]

    must_have_results = []
    missing_must_haves = []

    for cat in categories:
        req_list = must_have_reqs.get(cat, [])
        for req in req_list:
            eval_res = evaluate_requirement(cat, req, candidate_info, cv_text)
            must_have_results.append(eval_res)
            
            
            if eval_res["result"] == "Does Not Meet":
                missing_must_haves.append({
                    "category": cat,
                    "requirement": req,
                    "evidence": eval_res.get("evidence", "No evidence found")
                })

    is_qualified = (len(missing_must_haves) == 0)
    
    

    nice_to_have_results = []
    for cat in categories:
        req_list = nice_to_have_reqs.get(cat, [])
        for req in req_list:
            eval_res = evaluate_requirement(cat, req, candidate_info, cv_text)
            nice_to_have_results.append(eval_res)
            
            
            

    total_evals = must_have_results + nice_to_have_results
    total_points = 0.0
    max_possible_points = len(total_evals) * 1.0 if total_evals else 1.0

    for item in total_evals:
        if item["result"] == "Meets":
            total_points += 1.0
        elif item["result"] == "Partially Meets":
            total_points += 0.5

    match_percentage = round((total_points / max_possible_points) * 100, 1)

    return {
        "is_qualified": is_qualified,
        "score_percentage": match_percentage,
        "missing_must_haves": missing_must_haves,
        "must_have_results": must_have_results,
        "nice_to_have_results": nice_to_have_results,
        "all_results": total_evals
        
        
    }








def rank_and_filter_candidates(
    candidates_list: List[Dict[str, Any]],
    top_n: int = 20
) -> Dict[str, Any]:
    
    
    qualified = []
    non_qualified = []

    for candidate in candidates_list:
        
        
        if candidate.get("evaluation", {}).get("is_qualified", False):
            qualified.append(candidate)
        else:
            non_qualified.append(candidate)
            
            
            
            
            
            
            

    qualified.sort(
        key=lambda c: c.get("evaluation", {}).get("score_percentage", 0.0),
        reverse=True
    )



    non_qualified.sort(
        key=lambda c: c.get("evaluation", {}).get("score_percentage", 0.0),
        reverse=True
    )

    shortlist = qualified[:top_n]

    return {
        "qualified": qualified,
        "non_qualified": non_qualified,
        "shortlist": shortlist,
        "total_screened": len(candidates_list),
        "total_qualified": len(qualified),
        "total_non_qualified": len(non_qualified)
    }
    
    