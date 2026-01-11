"""
Multi-Objective Optimization Example

This example demonstrates multi-objective optimization using BOA,
optimizing two competing objectives simultaneously.
"""

import numpy as np

from boa.sdk import BOAClient, Campaign

# Define a multi-objective optimization problem
PROCESS_SPEC = """
name: binh_korn
version: 1

inputs:
  - name: x1
    type: continuous
    bounds: [0, 5]
    
  - name: x2
    type: continuous
    bounds: [0, 3]

objectives:
  - name: f1
    direction: minimize
    
  - name: f2
    direction: minimize

constraints:
  - expr: "(x1 - 5)**2 + x2**2 <= 25"
  - expr: "(x1 - 8)**2 + (x2 + 3)**2 >= 7.7"

strategies:
  default:
    sampler: lhs
    model: gp_matern
    acquisition: qnehvi
    ref_point: [140.0, 50.0]
"""


def binh_korn(x1: float, x2: float) -> tuple[float, float]:
    """
    Binh and Korn function (constrained multi-objective benchmark).
    
    f1(x) = 4*x1^2 + 4*x2^2
    f2(x) = (x1-5)^2 + (x2-5)^2
    
    Subject to:
    - (x1-5)^2 + x2^2 <= 25
    - (x1-8)^2 + (x2+3)^2 >= 7.7
    """
    f1 = 4 * x1**2 + 4 * x2**2
    f2 = (x1 - 5)**2 + (x2 - 5)**2
    return f1, f2


def check_constraints(x1: float, x2: float) -> bool:
    """Check if point satisfies constraints."""
    c1 = (x1 - 5)**2 + x2**2 <= 25
    c2 = (x1 - 8)**2 + (x2 + 3)**2 >= 7.7
    return c1 and c2


def main():
    # Connect to BOA server
    client = BOAClient("http://localhost:8000")
    
    try:
        health = client.health()
        print(f"Server status: {health['status']}")
    except Exception as e:
        print(f"Could not connect to server: {e}")
        print("Please start the server with: boa serve")
        return
    
    # Create process
    print("\n=== Creating Process ===")
    process = client.create_process("binh_korn", PROCESS_SPEC)
    print(f"Process ID: {process['id']}")
    
    # Create campaign
    print("\n=== Creating Campaign ===")
    campaign = Campaign.create(
        client, 
        process["id"], 
        "multi_objective_run",
        metadata={"benchmark": "binh_korn"}
    )
    print(f"Campaign ID: {campaign.id}")
    
    # Generate initial design
    print("\n=== Initial Design ===")
    proposals = campaign.initial_design(n_samples=15)
    campaign.accept_all(proposals)
    
    # Run initial experiments
    print("\n=== Running Initial Experiments ===")
    for candidate in proposals[0].candidates:
        x1, x2 = candidate["x1"], candidate["x2"]
        f1, f2 = binh_korn(x1, x2)
        feasible = check_constraints(x1, x2)
        
        campaign.add_observation(candidate, {"f1": f1, "f2": f2})
        status = "✓" if feasible else "✗"
        print(f"  {status} x1={x1:.2f}, x2={x2:.2f} -> f1={f1:.2f}, f2={f2:.2f}")
    
    # Optimization loop
    print("\n=== Optimization Loop ===")
    
    for iteration in range(30):
        # Get next suggestions (batch of 3)
        proposals = campaign.propose(n_candidates=3)
        campaign.accept_all(proposals)
        
        # Run experiments
        for candidate in proposals[0].candidates:
            x1, x2 = candidate["x1"], candidate["x2"]
            f1, f2 = binh_korn(x1, x2)
            campaign.add_observation(candidate, {"f1": f1, "f2": f2})
        
        # Check progress
        metrics = campaign.metrics()
        print(f"Iteration {iteration+1}: "
              f"Pareto size={metrics.pareto_front_size}, "
              f"Hypervolume={metrics.hypervolume:.2f}")
    
    # Final results
    print("\n=== Final Results ===")
    metrics = campaign.metrics()
    pareto_front = campaign.pareto_front()
    
    print(f"Total observations: {metrics.n_observations}")
    print(f"Final hypervolume: {metrics.hypervolume:.4f}")
    print(f"Pareto front size: {len(pareto_front)}")
    
    print("\n=== Pareto Front ===")
    for i, solution in enumerate(pareto_front):
        x = solution['x_raw']
        y = solution['y']
        print(f"  {i+1}. x1={x['x1']:.3f}, x2={x['x2']:.3f} -> f1={y['f1']:.2f}, f2={y['f2']:.2f}")
    
    # Complete campaign
    campaign.complete()
    print("\nCampaign completed!")
    
    # Optional: Visualize
    try:
        import matplotlib.pyplot as plt
        
        # Get all observations
        observations = campaign.get_observations()
        f1_vals = [obs.y["f1"] for obs in observations]
        f2_vals = [obs.y["f2"] for obs in observations]
        
        # Pareto front
        pf_f1 = [sol['y']['f1'] for sol in pareto_front]
        pf_f2 = [sol['y']['f2'] for sol in pareto_front]
        
        plt.figure(figsize=(10, 6))
        plt.scatter(f1_vals, f2_vals, c='blue', alpha=0.5, label='All observations')
        plt.scatter(pf_f1, pf_f2, c='red', s=100, marker='*', label='Pareto front')
        plt.xlabel('f1 (minimize)')
        plt.ylabel('f2 (minimize)')
        plt.title('Binh-Korn Multi-Objective Optimization')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig('pareto_front.png', dpi=150, bbox_inches='tight')
        print("\nPlot saved to pareto_front.png")
    except ImportError:
        print("\nInstall matplotlib for visualization: pip install matplotlib")


if __name__ == "__main__":
    main()





