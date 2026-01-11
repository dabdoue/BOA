#!/usr/bin/env python3
"""
BOA Demo - Multi-Objective Optimization

This demo shows BOA optimizing a multi-objective benchmark function.
"""

import sys
sys.path.insert(0, 'src')

from boa.sdk import BOAClient, Campaign

# Define the optimization problem
PROCESS_SPEC = """
name: demo_branin_currin
version: 1

inputs:
  - name: x1
    type: continuous
    bounds: [0, 1]
    
  - name: x2
    type: continuous
    bounds: [0, 1]

objectives:
  - name: branin
    direction: minimize
    
  - name: currin
    direction: minimize

strategies:
  default:
    sampler: lhs
    model: gp_matern
    acquisition: random
"""


def branin(x1: float, x2: float) -> float:
    """Branin function (rescaled to [0,1]^2)."""
    import math
    # Rescale
    x1_scaled = x1 * 15 - 5
    x2_scaled = x2 * 15
    
    a = 1
    b = 5.1 / (4 * math.pi**2)
    c = 5 / math.pi
    r = 6
    s = 10
    t = 1 / (8 * math.pi)
    
    result = a * (x2_scaled - b * x1_scaled**2 + c * x1_scaled - r)**2
    result += s * (1 - t) * math.cos(x1_scaled) + s
    
    return result


def currin(x1: float, x2: float) -> float:
    """Currin function."""
    import math
    
    if x2 == 0:
        x2 = 0.0001
    
    factor1 = 1 - math.exp(-1 / (2 * x2))
    factor2 = 2300 * x1**3 + 1900 * x1**2 + 2092 * x1 + 60
    factor3 = 100 * x1**3 + 500 * x1**2 + 4 * x1 + 20
    
    return factor1 * factor2 / factor3


def main():
    print("=" * 60)
    print("   BOA DEMO - Multi-Objective Bayesian Optimization")
    print("=" * 60)
    print()
    
    # Connect to server
    print("Connecting to BOA server at http://localhost:8020...")
    client = BOAClient("http://localhost:8020")
    
    try:
        health = client.health()
        print(f"✓ Server status: {health['status']}")
        print(f"✓ Version: {health['version']}")
        print(f"✓ Database: {health['database']}")
    except Exception as e:
        print(f"✗ Could not connect: {e}")
        return
    
    # Create process
    print()
    print("Creating optimization process...")
    process = client.create_process("branin_currin", PROCESS_SPEC)
    print(f"✓ Process ID: {process['id'][:8]}...")
    print(f"  Name: {process['name']}")
    print(f"  Objectives: branin (minimize), currin (minimize)")
    
    # Create campaign
    print()
    print("Creating optimization campaign...")
    campaign_data = client.create_campaign(
        process_id=process["id"],
        name="demo_run",
        metadata={"demo": True}
    )
    campaign = Campaign(client, campaign_data["id"])
    print(f"✓ Campaign ID: {campaign.campaign_id}")
    
    # Initial design
    print()
    print("Generating initial design (10 samples, Latin Hypercube)...")
    proposals = campaign.initial_design(n_samples=10)
    campaign.accept_all(proposals)
    print(f"✓ Generated {len(proposals[0].candidates)} initial samples")
    
    # Run initial experiments
    print()
    print("Running initial experiments:")
    for i, candidate in enumerate(proposals[0].candidates):
        x1, x2 = candidate["x1"], candidate["x2"]
        b = branin(x1, x2)
        c = currin(x1, x2)
        
        campaign.add_observation(candidate, {"branin": b, "currin": c})
        print(f"  {i+1:2d}. x1={x1:.3f}, x2={x2:.3f} -> branin={b:7.2f}, currin={c:.2f}")
    
    # Optimization loop
    print()
    print("Starting Bayesian optimization (15 iterations, batch=3)...")
    print("-" * 60)
    
    for iteration in range(15):
        # Get proposals from the model
        proposals = campaign.propose(n_candidates=3)
        campaign.accept_all(proposals)
        
        # Run experiments
        for candidate in proposals[0].candidates:
            x1, x2 = candidate["x1"], candidate["x2"]
            b = branin(x1, x2)
            c = currin(x1, x2)
            campaign.add_observation(candidate, {"branin": b, "currin": c})
        
        # Check progress
        metrics = campaign.metrics()
        pf_size = metrics.get('pareto_front_size') or 0
        hv = metrics.get('hypervolume') or 0
        print(f"Iteration {iteration+1:2d}: "
              f"Pareto size={pf_size:2d}, "
              f"Hypervolume={hv:.2f}")
    
    # Final results
    print("-" * 60)
    print()
    print("=" * 60)
    print("   FINAL RESULTS")
    print("=" * 60)
    
    metrics = campaign.metrics()
    pareto_front = campaign.pareto_front()
    
    print(f"\nTotal experiments: {metrics.get('n_observations', 0)}")
    print(f"Total iterations: {metrics.get('n_iterations', 0)}")
    hv = metrics.get('hypervolume')
    print(f"Final hypervolume: {hv:.4f}" if hv else "Final hypervolume: N/A")
    print(f"Pareto front size: {len(pareto_front)}")
    
    print("\nPareto optimal solutions:")
    print("-" * 60)
    print(f"{'#':<3} {'x1':<8} {'x2':<8} {'branin':<12} {'currin':<10}")
    print("-" * 60)
    
    for i, sol in enumerate(sorted(pareto_front, key=lambda s: s['y']['branin'])):
        x = sol['x_raw']
        y = sol['y']
        print(f"{i+1:<3} {x['x1']:<8.4f} {x['x2']:<8.4f} {y['branin']:<12.4f} {y['currin']:<10.4f}")
    
    # Complete campaign
    campaign.complete()
    print()
    print("✓ Campaign completed successfully!")
    print()
    
    # Export option
    print("To export this campaign, run:")
    print(f"  boa export {campaign.campaign_id} --output demo_results.json")


if __name__ == "__main__":
    main()

