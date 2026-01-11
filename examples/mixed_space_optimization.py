"""
Mixed Variable Space Optimization Example

This example demonstrates optimization with mixed variable types:
- Continuous variables
- Discrete (integer) variables
- Categorical variables
"""

import random

from boa.sdk import BOAClient, Campaign

# Define a problem with mixed variable types
PROCESS_SPEC = """
name: material_synthesis
version: 1

inputs:
  # Continuous variable: temperature
  - name: temperature
    type: continuous
    bounds: [300, 800]  # Kelvin
    
  # Continuous variable: pressure
  - name: pressure
    type: continuous
    bounds: [1, 50]  # bar
    
  # Discrete variable: number of layers
  - name: n_layers
    type: discrete
    bounds: [1, 10]
    
  # Categorical variable: material type
  - name: material
    type: categorical
    levels: [silicon, germanium, gallium_arsenide, indium_phosphide]
    
  # Categorical variable: deposition method
  - name: method
    type: categorical
    levels: [cvd, pvd, ald, mbe]

objectives:
  - name: efficiency
    direction: maximize
    
  - name: uniformity
    direction: maximize

strategies:
  default:
    sampler: lhs_optimized
    model: gp_matern
    acquisition: qnehvi
    ref_point: [0.0, 0.0]
"""


# Material properties for simulation
MATERIAL_PROPERTIES = {
    "silicon": {"base_eff": 0.6, "opt_temp": 500, "opt_press": 20},
    "germanium": {"base_eff": 0.55, "opt_temp": 450, "opt_press": 15},
    "gallium_arsenide": {"base_eff": 0.7, "opt_temp": 600, "opt_press": 25},
    "indium_phosphide": {"base_eff": 0.65, "opt_temp": 550, "opt_press": 30},
}

METHOD_MODIFIERS = {
    "cvd": {"eff_mult": 1.0, "uniformity": 0.8},
    "pvd": {"eff_mult": 0.9, "uniformity": 0.9},
    "ald": {"eff_mult": 0.95, "uniformity": 0.95},
    "mbe": {"eff_mult": 1.05, "uniformity": 0.7},
}


def simulate_synthesis(
    temperature: float,
    pressure: float,
    n_layers: int,
    material: str,
    method: str
) -> tuple[float, float]:
    """
    Simulated material synthesis experiment.
    
    Returns (efficiency, uniformity) based on input parameters.
    """
    # Get material properties
    props = MATERIAL_PROPERTIES[material]
    mods = METHOD_MODIFIERS[method]
    
    # Calculate efficiency based on temperature and pressure optimality
    temp_diff = abs(temperature - props["opt_temp"]) / 500
    press_diff = abs(pressure - props["opt_press"]) / 50
    
    base_efficiency = props["base_eff"] * mods["eff_mult"]
    efficiency = base_efficiency * (1 - 0.5 * temp_diff) * (1 - 0.3 * press_diff)
    
    # Layer effect: diminishing returns after optimal number
    optimal_layers = 5
    layer_effect = 1 - 0.05 * abs(n_layers - optimal_layers)
    efficiency *= layer_effect
    
    # Uniformity based on method and parameters
    uniformity = mods["uniformity"]
    uniformity *= (1 - 0.1 * temp_diff)  # Higher temp variance reduces uniformity
    uniformity *= (1 - 0.2 * (n_layers - 1) / 9)  # More layers reduce uniformity
    
    # Add some noise
    efficiency += random.gauss(0, 0.01)
    uniformity += random.gauss(0, 0.01)
    
    # Clamp values
    efficiency = max(0.0, min(1.0, efficiency))
    uniformity = max(0.0, min(1.0, uniformity))
    
    return efficiency, uniformity


def main():
    # Set seed for reproducibility
    random.seed(42)
    
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
    process = client.create_process("material_synthesis", PROCESS_SPEC)
    print(f"Process ID: {process['id']}")
    
    # Create campaign
    print("\n=== Creating Campaign ===")
    campaign = Campaign.create(client, process["id"], "synthesis_optimization")
    print(f"Campaign ID: {campaign.id}")
    
    # Generate initial design
    print("\n=== Initial Design ===")
    proposals = campaign.initial_design(n_samples=20)
    campaign.accept_all(proposals)
    
    print(f"Generated {len(proposals[0].candidates)} initial samples")
    
    # Run initial experiments
    print("\n=== Running Initial Experiments ===")
    for candidate in proposals[0].candidates:
        efficiency, uniformity = simulate_synthesis(**candidate)
        campaign.add_observation(candidate, {
            "efficiency": efficiency,
            "uniformity": uniformity
        })
        print(f"  {candidate['material']:20s} | {candidate['method']:3s} | "
              f"T={candidate['temperature']:5.0f}K | P={candidate['pressure']:5.1f}bar | "
              f"layers={candidate['n_layers']:2d} -> "
              f"eff={efficiency:.3f}, uni={uniformity:.3f}")
    
    # Optimization loop
    print("\n=== Optimization Loop ===")
    
    for iteration in range(25):
        # Get suggestions
        proposals = campaign.propose(n_candidates=4)
        campaign.accept_all(proposals)
        
        # Run experiments
        for candidate in proposals[0].candidates:
            efficiency, uniformity = simulate_synthesis(**candidate)
            campaign.add_observation(candidate, {
                "efficiency": efficiency,
                "uniformity": uniformity
            })
        
        # Check progress
        metrics = campaign.metrics()
        print(f"Iteration {iteration+1}: "
              f"Pareto size={metrics.pareto_front_size}, "
              f"HV={metrics.hypervolume:.4f}")
    
    # Final results
    print("\n=== Final Results ===")
    metrics = campaign.metrics()
    pareto_front = campaign.pareto_front()
    
    print(f"Total experiments: {metrics.n_observations}")
    print(f"Final hypervolume: {metrics.hypervolume:.4f}")
    print(f"Pareto front size: {len(pareto_front)}")
    
    print("\n=== Pareto Optimal Solutions ===")
    print(f"{'Material':<20} {'Method':<5} {'Temp':<7} {'Press':<7} {'Layers':<7} {'Efficiency':<10} {'Uniformity':<10}")
    print("-" * 85)
    
    for solution in sorted(pareto_front, key=lambda x: -x['y']['efficiency']):
        x = solution['x_raw']
        y = solution['y']
        print(f"{x['material']:<20} {x['method']:<5} {x['temperature']:<7.0f} "
              f"{x['pressure']:<7.1f} {x['n_layers']:<7} "
              f"{y['efficiency']:<10.4f} {y['uniformity']:<10.4f}")
    
    # Analysis of best conditions per material
    print("\n=== Best Efficiency per Material ===")
    observations = campaign.get_observations()
    
    for material in MATERIAL_PROPERTIES.keys():
        material_obs = [obs for obs in observations if obs.x_raw['material'] == material]
        if material_obs:
            best = max(material_obs, key=lambda x: x.y['efficiency'])
            print(f"{material}: efficiency={best.y['efficiency']:.4f} "
                  f"(T={best.x_raw['temperature']:.0f}K, "
                  f"P={best.x_raw['pressure']:.1f}bar, "
                  f"method={best.x_raw['method']})")
    
    # Complete campaign
    campaign.complete()
    print("\nCampaign completed!")


if __name__ == "__main__":
    main()





