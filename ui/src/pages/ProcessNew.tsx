import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  FlaskConical, 
  ArrowLeft,
  Save,
  Sparkles
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ProcessBuilder } from '@/components/ProcessBuilder';
import { useCreateProcess } from '@/hooks/useApi';

const TEMPLATES: Record<string, { name: string; description: string; yaml: string }> = {
  ald: {
    name: 'ALD Process Optimization',
    description: 'Optimize Atomic Layer Deposition parameters for thin film quality',
    yaml: `name: ald-optimization
description: Optimize ALD parameters for thin film deposition

inputs:
  - name: temperature
    type: continuous
    bounds: [150, 350]
    description: Substrate temperature (°C)
  - name: pulse_time
    type: continuous
    bounds: [0.02, 0.5]
    description: Precursor pulse time (seconds)
  - name: purge_time
    type: continuous
    bounds: [2, 20]
    description: Purge time between pulses (seconds)
  - name: cycles
    type: discrete
    values: [50, 100, 150, 200, 250, 300]
    description: Number of ALD cycles
  - name: precursor
    type: categorical
    values: [TMA, DEZ, TDMAT]
    description: Precursor type

objectives:
  - name: thickness_uniformity
    direction: maximize
    description: Film thickness uniformity across wafer
  - name: growth_rate
    direction: maximize
    description: Deposition rate (nm/cycle)
  - name: defect_density
    direction: minimize
    description: Surface defect count

strategies:
  default:
    sampler: lhs
    model: gp_matern
    acquisition: random
    n_initial: 10
`,
  },
  spincoating: {
    name: 'Spin Coating Optimization',
    description: 'Optimize spin coating parameters for uniform thin films',
    yaml: `name: spincoating-optimization
description: Optimize spin coating for thin film uniformity

inputs:
  - name: spin_speed
    type: continuous
    bounds: [500, 6000]
    description: Rotation speed (RPM)
  - name: spin_time
    type: continuous
    bounds: [10, 120]
    description: Spin duration (seconds)
  - name: acceleration
    type: continuous
    bounds: [100, 2000]
    description: Ramp rate (RPM/s)
  - name: solution_concentration
    type: continuous
    bounds: [5, 50]
    description: Solution concentration (mg/mL)
  - name: solvent
    type: categorical
    values: [chlorobenzene, DMF, DMSO, toluene]
    description: Solvent type

objectives:
  - name: thickness
    target: 100
    description: Target film thickness (nm)
  - name: uniformity
    direction: maximize
    description: Thickness uniformity (%)
  - name: roughness
    direction: minimize
    description: Surface roughness (nm RMS)

strategies:
  default:
    sampler: sobol
    model: gp_matern
    acquisition: random
    n_initial: 8
`,
  },
  perovskite: {
    name: 'Perovskite Stability Optimization',
    description: 'Optimize perovskite composition for maximum stability',
    yaml: `name: perovskite-stability
description: Optimize perovskite solar cell stability

inputs:
  - name: ma_fraction
    type: continuous
    bounds: [0, 1]
    description: Methylammonium fraction
  - name: fa_fraction
    type: continuous
    bounds: [0, 1]
    description: Formamidinium fraction
  - name: cs_fraction
    type: continuous
    bounds: [0, 0.2]
    description: Cesium fraction
  - name: br_fraction
    type: continuous
    bounds: [0, 0.4]
    description: Bromide fraction
  - name: annealing_temp
    type: continuous
    bounds: [80, 150]
    description: Annealing temperature (°C)
  - name: annealing_time
    type: continuous
    bounds: [5, 60]
    description: Annealing time (minutes)

objectives:
  - name: pce
    direction: maximize
    description: Power conversion efficiency (%)
  - name: t80_lifetime
    direction: maximize
    description: Time to 80% of initial PCE (hours)
  - name: hysteresis_index
    direction: minimize
    description: J-V hysteresis index

constraints:
  - type: sum_equals
    inputs: [ma_fraction, fa_fraction, cs_fraction]
    value: 1.0
    description: Cation fractions must sum to 1

strategies:
  default:
    sampler: lhs
    model: gp_rbf
    acquisition: random
    n_initial: 15
`,
  },
  blank: {
    name: 'Blank Template',
    description: 'Start with a minimal template',
    yaml: `name: my-optimization
description: Custom optimization process

inputs:
  - name: x1
    type: continuous
    bounds: [0, 1]
  - name: x2
    type: continuous
    bounds: [0, 1]

objectives:
  - name: y1
    direction: minimize
  - name: y2
    direction: minimize

strategies:
  default:
    sampler: lhs
    model: gp_matern
    acquisition: random
    n_initial: 5
`,
  },
};

export function ProcessNew() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const template = searchParams.get('template') || 'blank';

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [specYaml, setSpecYaml] = useState('');

  const createProcess = useCreateProcess();

  useEffect(() => {
    const t = TEMPLATES[template] || TEMPLATES.blank;
    setName(t.name);
    setDescription(t.description);
    setSpecYaml(t.yaml);
  }, [template]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const process = await createProcess.mutateAsync({
        name,
        description,
        spec_yaml: specYaml,
      });
      navigate(`/processes/${process.id}`);
    } catch (error) {
      console.error('Failed to create process:', error);
      alert(error instanceof Error ? error.message : 'Failed to create process');
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">New Process</h1>
            <p className="text-[hsl(var(--muted-foreground))] mt-1">
              Define your optimization specification
            </p>
          </div>
        </div>
        <Button 
          onClick={handleSubmit} 
          disabled={createProcess.isPending} 
          className="gap-2"
          size="lg"
        >
          <Save className="h-4 w-4" />
          {createProcess.isPending ? 'Creating...' : 'Create Process'}
        </Button>
      </div>

      {/* Template Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-[hsl(var(--accent))]" />
            Choose a Template
          </CardTitle>
          <CardDescription>
            Start with a pre-built template or create from scratch
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(TEMPLATES).map(([key, t]) => (
              <button
                key={key}
                type="button"
                onClick={() => navigate(`/processes/new?template=${key}`, { replace: true })}
                className={`p-4 rounded-lg border text-left transition-all ${
                  template === key
                    ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/10'
                    : 'border-[hsl(var(--border))] hover:border-[hsl(var(--primary))]/50'
                }`}
              >
                <div className="font-medium text-sm">{t.name}</div>
                <div className="text-xs text-[hsl(var(--muted-foreground))] mt-1 line-clamp-2">
                  {t.description}
                </div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Process Builder */}
      <ProcessBuilder
        initialYaml={specYaml}
        onSpecChange={(_, yaml) => setSpecYaml(yaml)}
        onNameChange={setName}
        onDescriptionChange={setDescription}
      />
    </div>
  );
}
