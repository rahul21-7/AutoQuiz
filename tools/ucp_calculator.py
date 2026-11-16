#!/usr/bin/env python3
"""
Python mirror of UCP Estimation Calculator matching report pages 75-82.
"""

def calculate_ucp(productivity_factor: float = 8.0):
    # Unadjusted Use Case Weight (UUCW)
    simple_uc = 8
    average_uc = 7
    complex_uc = 5
    uucw = (simple_uc * 5) + (average_uc * 10) + (complex_uc * 15) # 185

    # Unadjusted Actor Weight (UAW)
    simple_actor = 4
    average_actor = 1
    complex_actor = 1
    uaw = (simple_actor * 1) + (average_actor * 2) + (complex_actor * 3) # 9

    uucp = uucw + uaw # 194

    # Technical Complexity Factors (TCF)
    tcf_factors = {
        "Distributed system": (2.0, 1.0),
        "Response time/performance objectives": (1.0, 4.0),
        "End-user efficiency": (1.0, 4.0),
        "Internal processing complexity": (1.0, 5.0),
        "Code reusability": (1.0, 3.0),
        "Easy to install": (0.5, 3.0),
        "Easy to use": (0.5, 4.0),
        "Portability to other platforms": (2.0, 3.0),
        "System maintenance": (1.0, 3.0),
        "Concurrent/parallel processing": (1.0, 3.0),
        "Security features": (1.0, 5.0),
        "Access for third parties": (1.0, 1.0),
        "End user training": (1.0, 2.0)
    }
    tf_sum = sum(w * r for w, r in tcf_factors.values())
    tcf = 0.6 + (tf_sum / 100.0) # 1.01500

    # Environmental Complexity Factors (ECF)
    ecf_factors = {
        "Familiar with development process used": (1.5, 4.0),
        "Application experience": (0.5, 3.0),
        "Object-oriented experience of team": (1.0, 4.0),
        "Lead analyst capability": (0.5, 3.0),
        "Motivation of the team": (1.0, 5.0),
        "Stability of Requirements": (2.0, 4.0),
        "Part-time staff": (-1.0, 2.0),
        "Difficult programming language": (-1.0, 1.0)
    }
    ef_sum = sum(w * r for w, r in ecf_factors.values())
    ecf = 1.4 + (-0.03 * ef_sum) # 0.71000

    ucp = uucp * tcf * ecf
    effort = ucp * productivity_factor

    print("=========================================================")
    print(" AUTOQUIZ AI PLATFORM - UCP ESTIMATION CALCULATOR")
    print("=========================================================")
    print(f"UUCW (Unadjusted Use Case Weight) : {uucw}")
    print(f"UAW (Unadjusted Actor Weight) : {uaw}")
    print(f"UUCP (Unadjusted Use Case Points) : {uucp}")
    print(f"TCF (Technical Complexity Factor) : {tcf:.5f}")
    print(f"ECF (Environmental Complexity Factor): {ecf:.5f}")
    print(f"UCP (Adjusted Use Case Points) : {ucp:.5f}")
    print(f"Estimated Total Effort : {effort:.5f} person-hours")

    return {
        "uucw": uucw,
        "uaw": uaw,
        "uucp": uucp,
        "tcf": round(tcf, 5),
        "ecf": round(ecf, 5),
        "ucp": round(ucp, 5),
        "total_effort_hours": round(effort, 2)
    }

if __name__ == "__main__":
    calculate_ucp()

