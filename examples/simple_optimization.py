"""
Simple Single-Objective Optimization Example

This example demonstrates basic usage of BOA for single-objective optimization.
"""

from boa.sdk import BOAClient, Campaign

# Define the optimization problem
PROCESS_SPEC = """
name: simple_quadratic
version: 1

inputs:
  - name: x
    type: continuous
    bounds: [-5, 5]
    
  - name: y
    type: continuous
    bounds: [-5, 5]

objectives:
  - name: z
    direction: minimize

strategies:
  default:
    sampler: lhs
    model: gp_matern
    acquisition: expected_improvement
"""


def objective_function(x: float, y: float) -> float:
    """
    Rosenbrock function (classic optimization benchmark).
    Minimum at (1, 1) with value 0.
    """
    return (1 - x) ** 2 + 100 * (y - x**2) ** 2


def main():
    # Connect to BOA server
    client = BOAClient("http://localhost:8000")
    
    try:
        # Check server health
        health = client.health()
        print(f"Server status: {health['status']}")
    except Exception as e:
        print(f"Could not connect to server: {e}")
        print("Please start the server with: boa serve")
        return
    
    # Create process
    print("\n=== Creating Process ===")
    process = client.create_process("rosenbrock", PROCESS_SPEC)
    print(f"Process ID: {process['id']}")
    
    # Create campaign
    print("\n=== Creating Campaign ===")
    campaign = Campaign.create(client, process["id"], "optimization_run")
    print(f"Campaign ID: {campaign.id}")
    
    # Generate initial design
    print("\n=== Initial Design ===")
    proposals = campaign.initial_design(n_samples=10)
    campaign.accept_all(proposals)
    
    print(f"Generated {len(proposals[0].candidates)} initial samples")
    
    # Run initial experiments
    print("\n=== Running Initial Experiments ===")
    for i, candidate in enumerate(proposals[0].candidates):
        result = objective_function(candidate["x"], candidate["y"])
        campaign.add_observation(candidate, {"z": result})
        print(f"  Sample {i+1}: x={candidate['x']:.3f}, y={candidate['y']:.3f} -> z={result:.3f}")
    
    # Optimization loop
    print("\n=== Optimization Loop ===")
    best_value = float("inf")
    
    for iteration in range(20):
        # Get next suggestion
        proposals = campaign.propose(n_candidates=1)
        campaign.accept_all(proposals)
        
        candidate = proposals[0].candidates[0]
        
        # Run experiment
        result = objective_function(candidate["x"], candidate["y"])
        campaign.add_observation(candidate, {"z": result})
        
        # Track best
        if result < best_value:
            best_value = result
            print(f"Iteration {iteration+1}: x={candidate['x']:.3f}, y={candidate['y']:.3f} -> z={result:.3f} (NEW BEST)")
        else:
            print(f"Iteration {iteration+1}: x={candidate['x']:.3f}, y={candidate['y']:.3f} -> z={result:.3f}")
    
    # Final results
    print("\n=== Final Results ===")
    metrics = campaign.metrics()
    best = campaign.best()
    
    print(f"Total observations: {metrics.n_observations}")
    print(f"Best inputs: x={best['x_raw']['x']:.4f}, y={best['x_raw']['y']:.4f}")
    print(f"Best value: z={best['y']['z']:.4f}")
    print(f"True minimum: (1, 1) -> 0")
    
    # Complete campaign
    campaign.complete()
    print("\nCampaign completed!")


if __name__ == "__main__":
    main()





