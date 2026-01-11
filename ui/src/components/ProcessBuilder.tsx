import { useState, useEffect, useCallback } from 'react';
import { 
  Plus, 
  Trash2, 
  GripVertical,
  ChevronDown,
  ChevronUp,
  Layers,
  Target,
  Settings2,
  AlertTriangle,
  FileCode
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import * as yaml from 'js-yaml';

// Types
interface InputSpec {
  name: string;
  type: 'continuous' | 'discrete' | 'categorical';
  bounds?: [number, number];
  values?: (string | number)[];
  description?: string;
}

interface ObjectiveSpec {
  name: string;
  direction?: 'minimize' | 'maximize';
  target?: number;
  description?: string;
}

interface ConstraintSpec {
  type: 'sum_equals' | 'sum_less_than' | 'custom';
  inputs?: string[];
  value?: number;
  expression?: string;
  description?: string;
}

interface StrategySpec {
  sampler: string;
  model: string;
  acquisition: string;
  n_initial: number;
}

interface ProcessSpec {
  name: string;
  description: string;
  inputs: InputSpec[];
  objectives: ObjectiveSpec[];
  constraints?: ConstraintSpec[];
  strategies: Record<string, StrategySpec>;
}

interface ProcessBuilderProps {
  initialYaml?: string;
  onSpecChange: (spec: ProcessSpec, yamlStr: string) => void;
  onNameChange?: (name: string) => void;
  onDescriptionChange?: (description: string) => void;
}

const SAMPLERS = [
  { value: 'random', label: 'Random' },
  { value: 'lhs', label: 'Latin Hypercube (LHS)' },
  { value: 'lhs_optimized', label: 'Optimized LHS' },
  { value: 'sobol', label: 'Sobol Sequence' },
];

const MODELS = [
  { value: 'gp_matern', label: 'Gaussian Process (Matérn)' },
  { value: 'gp_rbf', label: 'Gaussian Process (RBF)' },
];

const ACQUISITIONS = [
  { value: 'random', label: 'Random' },
  { value: 'ei', label: 'Expected Improvement (EI)' },
  { value: 'ucb', label: 'Upper Confidence Bound (UCB)' },
  { value: 'qNEHVI', label: 'qNEHVI (Multi-objective)' },
  { value: 'qParEGO', label: 'qParEGO (Multi-objective)' },
];

function defaultSpec(): ProcessSpec {
  return {
    name: 'my-optimization',
    description: 'Custom optimization process',
    inputs: [
      { name: 'x1', type: 'continuous', bounds: [0, 1], description: '' },
    ],
    objectives: [
      { name: 'y1', direction: 'minimize', description: '' },
    ],
    constraints: [],
    strategies: {
      default: {
        sampler: 'lhs',
        model: 'gp_matern',
        acquisition: 'random',
        n_initial: 5,
      },
    },
  };
}

function specToYaml(spec: ProcessSpec): string {
  const obj: Record<string, unknown> = {
    name: spec.name,
    description: spec.description,
    inputs: spec.inputs.map(input => {
      const inp: Record<string, unknown> = {
        name: input.name,
        type: input.type,
      };
      if (input.type === 'continuous' && input.bounds) {
        inp.bounds = input.bounds;
      }
      if ((input.type === 'discrete' || input.type === 'categorical') && input.values) {
        inp.values = input.values;
      }
      if (input.description) {
        inp.description = input.description;
      }
      return inp;
    }),
    objectives: spec.objectives.map(obj => {
      const o: Record<string, unknown> = { name: obj.name };
      if (obj.direction) o.direction = obj.direction;
      if (obj.target !== undefined) o.target = obj.target;
      if (obj.description) o.description = obj.description;
      return o;
    }),
    strategies: spec.strategies,
  };
  if (spec.constraints && spec.constraints.length > 0) {
    obj.constraints = spec.constraints;
  }
  return yaml.dump(obj, { indent: 2, lineWidth: -1 });
}

function yamlToSpec(yamlStr: string): ProcessSpec | null {
  try {
    const obj = yaml.load(yamlStr) as Record<string, unknown>;
    if (!obj) return null;
    
    const spec: ProcessSpec = {
      name: (obj.name as string) || 'my-optimization',
      description: (obj.description as string) || '',
      inputs: ((obj.inputs as Array<Record<string, unknown>>) || []).map(inp => ({
        name: inp.name as string,
        type: inp.type as 'continuous' | 'discrete' | 'categorical',
        bounds: inp.bounds as [number, number] | undefined,
        values: inp.values as (string | number)[] | undefined,
        description: inp.description as string | undefined,
      })),
      objectives: ((obj.objectives as Array<Record<string, unknown>>) || []).map(o => ({
        name: o.name as string,
        direction: o.direction as 'minimize' | 'maximize' | undefined,
        target: o.target as number | undefined,
        description: o.description as string | undefined,
      })),
      constraints: ((obj.constraints as Array<Record<string, unknown>>) || []).map(c => ({
        type: c.type as 'sum_equals' | 'sum_less_than' | 'custom',
        inputs: c.inputs as string[] | undefined,
        value: c.value as number | undefined,
        expression: c.expression as string | undefined,
        description: c.description as string | undefined,
      })),
      strategies: (obj.strategies as Record<string, StrategySpec>) || {
        default: { sampler: 'lhs', model: 'gp_matern', acquisition: 'random', n_initial: 5 }
      },
    };
    return spec;
  } catch {
    return null;
  }
}

// Input Editor Component
function InputEditor({ 
  input, 
  index, 
  onChange, 
  onRemove 
}: { 
  input: InputSpec; 
  index: number; 
  onChange: (input: InputSpec) => void;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="border border-[hsl(var(--border))] rounded-lg p-4 bg-[hsl(var(--card))]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GripVertical className="h-4 w-4 text-[hsl(var(--muted-foreground))] cursor-grab" />
          <Badge variant="secondary" className="font-mono">{index + 1}</Badge>
          <span className="font-medium">{input.name || 'Unnamed Input'}</span>
          <Badge variant="outline">{input.type}</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onRemove}
            className="text-[hsl(var(--destructive))] hover:text-[hsl(var(--destructive))]"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 grid gap-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Variable Name</Label>
              <Input
                value={input.name}
                onChange={(e) => onChange({ ...input, name: e.target.value })}
                placeholder="e.g., temperature"
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select
                value={input.type}
                onValueChange={(value) => {
                  const newInput = { ...input, type: value as InputSpec['type'] };
                  if (value === 'continuous') {
                    newInput.bounds = input.bounds || [0, 1];
                    delete newInput.values;
                  } else {
                    newInput.values = input.values || ['option1', 'option2'];
                    delete newInput.bounds;
                  }
                  onChange(newInput);
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="continuous">Continuous (numeric range)</SelectItem>
                  <SelectItem value="discrete">Discrete (numeric values)</SelectItem>
                  <SelectItem value="categorical">Categorical (text options)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {input.type === 'continuous' && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Minimum</Label>
                <Input
                  type="number"
                  value={input.bounds?.[0] ?? 0}
                  onChange={(e) => onChange({ 
                    ...input, 
                    bounds: [parseFloat(e.target.value), input.bounds?.[1] ?? 1] 
                  })}
                />
              </div>
              <div className="space-y-2">
                <Label>Maximum</Label>
                <Input
                  type="number"
                  value={input.bounds?.[1] ?? 1}
                  onChange={(e) => onChange({ 
                    ...input, 
                    bounds: [input.bounds?.[0] ?? 0, parseFloat(e.target.value)] 
                  })}
                />
              </div>
            </div>
          )}

          {(input.type === 'discrete' || input.type === 'categorical') && (
            <div className="space-y-2">
              <Label>Values (comma-separated)</Label>
              <Input
                value={(input.values || []).join(', ')}
                onChange={(e) => {
                  const values = e.target.value.split(',').map(v => {
                    const trimmed = v.trim();
                    if (input.type === 'discrete') {
                      const num = parseFloat(trimmed);
                      return isNaN(num) ? trimmed : num;
                    }
                    return trimmed;
                  }).filter(v => v !== '');
                  onChange({ ...input, values });
                }}
                placeholder={input.type === 'discrete' ? '10, 20, 30, 40' : 'option1, option2, option3'}
              />
            </div>
          )}

          <div className="space-y-2">
            <Label>Description (optional)</Label>
            <Input
              value={input.description || ''}
              onChange={(e) => onChange({ ...input, description: e.target.value })}
              placeholder="What does this variable represent?"
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Objective Editor Component
function ObjectiveEditor({ 
  objective, 
  index, 
  onChange, 
  onRemove 
}: { 
  objective: ObjectiveSpec; 
  index: number; 
  onChange: (objective: ObjectiveSpec) => void;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const [useTarget, setUseTarget] = useState(objective.target !== undefined);

  return (
    <div className="border border-[hsl(var(--border))] rounded-lg p-4 bg-[hsl(var(--card))]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GripVertical className="h-4 w-4 text-[hsl(var(--muted-foreground))] cursor-grab" />
          <Badge variant="secondary" className="font-mono">{index + 1}</Badge>
          <span className="font-medium">{objective.name || 'Unnamed Objective'}</span>
          <Badge variant={objective.direction === 'maximize' ? 'success' : 'destructive'}>
            {useTarget ? `target: ${objective.target}` : (objective.direction || 'minimize')}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onRemove}
            className="text-[hsl(var(--destructive))] hover:text-[hsl(var(--destructive))]"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 grid gap-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Objective Name</Label>
              <Input
                value={objective.name}
                onChange={(e) => onChange({ ...objective, name: e.target.value })}
                placeholder="e.g., efficiency"
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label>Optimization Type</Label>
              <Select
                value={useTarget ? 'target' : (objective.direction || 'minimize')}
                onValueChange={(value) => {
                  if (value === 'target') {
                    setUseTarget(true);
                    onChange({ ...objective, direction: undefined, target: 0 });
                  } else {
                    setUseTarget(false);
                    onChange({ ...objective, direction: value as 'minimize' | 'maximize', target: undefined });
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="minimize">Minimize</SelectItem>
                  <SelectItem value="maximize">Maximize</SelectItem>
                  <SelectItem value="target">Target Value</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {useTarget && (
            <div className="space-y-2">
              <Label>Target Value</Label>
              <Input
                type="number"
                value={objective.target ?? 0}
                onChange={(e) => onChange({ ...objective, target: parseFloat(e.target.value) })}
                placeholder="100"
              />
            </div>
          )}

          <div className="space-y-2">
            <Label>Description (optional)</Label>
            <Input
              value={objective.description || ''}
              onChange={(e) => onChange({ ...objective, description: e.target.value })}
              placeholder="What does this objective measure?"
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Strategy Editor Component
function StrategyEditor({ 
  strategy, 
  onChange 
}: { 
  strategy: StrategySpec; 
  onChange: (strategy: StrategySpec) => void;
}) {
  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Sampler</Label>
          <Select value={strategy.sampler} onValueChange={(v) => onChange({ ...strategy, sampler: v })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SAMPLERS.map(s => (
                <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Method for generating initial samples
          </p>
        </div>
        <div className="space-y-2">
          <Label>Surrogate Model</Label>
          <Select value={strategy.model} onValueChange={(v) => onChange({ ...strategy, model: v })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MODELS.map(m => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Model used to predict outcomes
          </p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Acquisition Function</Label>
          <Select value={strategy.acquisition} onValueChange={(v) => onChange({ ...strategy, acquisition: v })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ACQUISITIONS.map(a => (
                <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Strategy for selecting next experiments
          </p>
        </div>
        <div className="space-y-2">
          <Label>Initial Samples</Label>
          <Input
            type="number"
            min={1}
            max={100}
            value={strategy.n_initial}
            onChange={(e) => onChange({ ...strategy, n_initial: parseInt(e.target.value) || 5 })}
          />
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            Number of random samples before model-guided
          </p>
        </div>
      </div>
    </div>
  );
}

// Constraint Editor Component
function ConstraintEditor({ 
  constraint, 
  index, 
  inputNames,
  onChange, 
  onRemove 
}: { 
  constraint: ConstraintSpec; 
  index: number;
  inputNames: string[];
  onChange: (constraint: ConstraintSpec) => void;
  onRemove: () => void;
}) {
  return (
    <div className="border border-[hsl(var(--border))] rounded-lg p-4 bg-[hsl(var(--card))]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Badge variant="warning" className="font-mono">{index + 1}</Badge>
          <span className="font-medium">{constraint.type.replace('_', ' ')}</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onRemove}
          className="text-[hsl(var(--destructive))]"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      <div className="grid gap-4">
        <div className="space-y-2">
          <Label>Constraint Type</Label>
          <Select value={constraint.type} onValueChange={(v) => onChange({ ...constraint, type: v as ConstraintSpec['type'] })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sum_equals">Sum Equals</SelectItem>
              <SelectItem value="sum_less_than">Sum Less Than</SelectItem>
              <SelectItem value="custom">Custom Expression</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {constraint.type !== 'custom' && (
          <>
            <div className="space-y-2">
              <Label>Variables (comma-separated)</Label>
              <Input
                value={(constraint.inputs || []).join(', ')}
                onChange={(e) => onChange({ 
                  ...constraint, 
                  inputs: e.target.value.split(',').map(v => v.trim()).filter(v => v) 
                })}
                placeholder="x1, x2, x3"
              />
              {inputNames.length > 0 && (
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Available: {inputNames.join(', ')}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Value</Label>
              <Input
                type="number"
                value={constraint.value ?? 1}
                onChange={(e) => onChange({ ...constraint, value: parseFloat(e.target.value) })}
              />
            </div>
          </>
        )}

        {constraint.type === 'custom' && (
          <div className="space-y-2">
            <Label>Expression</Label>
            <Input
              value={constraint.expression || ''}
              onChange={(e) => onChange({ ...constraint, expression: e.target.value })}
              placeholder="x1 + x2 <= 1"
            />
          </div>
        )}

        <div className="space-y-2">
          <Label>Description (optional)</Label>
          <Input
            value={constraint.description || ''}
            onChange={(e) => onChange({ ...constraint, description: e.target.value })}
            placeholder="Why is this constraint needed?"
          />
        </div>
      </div>
    </div>
  );
}

// Main ProcessBuilder Component
export function ProcessBuilder({ initialYaml, onSpecChange, onNameChange, onDescriptionChange }: ProcessBuilderProps) {
  const [spec, setSpec] = useState<ProcessSpec>(defaultSpec);
  const [yamlStr, setYamlStr] = useState('');
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('form');

  // Initialize from YAML
  useEffect(() => {
    if (initialYaml) {
      const parsed = yamlToSpec(initialYaml);
      if (parsed) {
        setSpec(parsed);
        setYamlStr(initialYaml);
      }
    }
  }, [initialYaml]);

  // Sync form → YAML
  const updateSpec = useCallback((newSpec: ProcessSpec) => {
    setSpec(newSpec);
    const newYaml = specToYaml(newSpec);
    setYamlStr(newYaml);
    setYamlError(null);
    onSpecChange(newSpec, newYaml);
    if (onNameChange) onNameChange(newSpec.name);
    if (onDescriptionChange) onDescriptionChange(newSpec.description);
  }, [onSpecChange, onNameChange, onDescriptionChange]);

  // Sync YAML → form
  const handleYamlChange = useCallback((newYaml: string) => {
    setYamlStr(newYaml);
    const parsed = yamlToSpec(newYaml);
    if (parsed) {
      setSpec(parsed);
      setYamlError(null);
      onSpecChange(parsed, newYaml);
      if (onNameChange) onNameChange(parsed.name);
      if (onDescriptionChange) onDescriptionChange(parsed.description);
    } else {
      setYamlError('Invalid YAML syntax');
    }
  }, [onSpecChange, onNameChange, onDescriptionChange]);

  // Input handlers
  const addInput = () => {
    const newInputs = [...spec.inputs, { name: `x${spec.inputs.length + 1}`, type: 'continuous' as const, bounds: [0, 1] as [number, number], description: '' }];
    updateSpec({ ...spec, inputs: newInputs });
  };

  const updateInput = (index: number, input: InputSpec) => {
    const newInputs = [...spec.inputs];
    newInputs[index] = input;
    updateSpec({ ...spec, inputs: newInputs });
  };

  const removeInput = (index: number) => {
    const newInputs = spec.inputs.filter((_, i) => i !== index);
    updateSpec({ ...spec, inputs: newInputs });
  };

  // Objective handlers
  const addObjective = () => {
    const newObjectives = [...spec.objectives, { name: `y${spec.objectives.length + 1}`, direction: 'minimize' as const, description: '' }];
    updateSpec({ ...spec, objectives: newObjectives });
  };

  const updateObjective = (index: number, objective: ObjectiveSpec) => {
    const newObjectives = [...spec.objectives];
    newObjectives[index] = objective;
    updateSpec({ ...spec, objectives: newObjectives });
  };

  const removeObjective = (index: number) => {
    const newObjectives = spec.objectives.filter((_, i) => i !== index);
    updateSpec({ ...spec, objectives: newObjectives });
  };

  // Constraint handlers
  const addConstraint = () => {
    const newConstraints = [...(spec.constraints || []), { type: 'sum_equals' as const, inputs: [], value: 1, description: '' }];
    updateSpec({ ...spec, constraints: newConstraints });
  };

  const updateConstraint = (index: number, constraint: ConstraintSpec) => {
    const newConstraints = [...(spec.constraints || [])];
    newConstraints[index] = constraint;
    updateSpec({ ...spec, constraints: newConstraints });
  };

  const removeConstraint = (index: number) => {
    const newConstraints = (spec.constraints || []).filter((_, i) => i !== index);
    updateSpec({ ...spec, constraints: newConstraints });
  };

  // Strategy handler
  const updateStrategy = (strategy: StrategySpec) => {
    updateSpec({ ...spec, strategies: { ...spec.strategies, default: strategy } });
  };

  const inputNames = spec.inputs.map(i => i.name);

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="form" className="gap-2">
          <Settings2 className="h-4 w-4" />
          Visual Builder
        </TabsTrigger>
        <TabsTrigger value="yaml" className="gap-2">
          <FileCode className="h-4 w-4" />
          YAML Editor
        </TabsTrigger>
      </TabsList>

      <TabsContent value="form" className="space-y-6 mt-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Process Name</Label>
                <Input
                  value={spec.name}
                  onChange={(e) => updateSpec({ ...spec, name: e.target.value })}
                  placeholder="my-optimization"
                  className="font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input
                  value={spec.description}
                  onChange={(e) => updateSpec({ ...spec, description: e.target.value })}
                  placeholder="What are you optimizing?"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Inputs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-5 w-5 text-[hsl(var(--primary))]" />
                  Input Variables
                </CardTitle>
                <CardDescription>
                  Define the parameters you want to optimize
                </CardDescription>
              </div>
              <Button onClick={addInput} size="sm" className="gap-2">
                <Plus className="h-4 w-4" />
                Add Input
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {spec.inputs.map((input, i) => (
                <InputEditor
                  key={i}
                  input={input}
                  index={i}
                  onChange={(inp) => updateInput(i, inp)}
                  onRemove={() => removeInput(i)}
                />
              ))}
              {spec.inputs.length === 0 && (
                <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
                  No inputs defined. Click "Add Input" to get started.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Objectives */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5 text-[hsl(var(--accent))]" />
                  Objectives
                </CardTitle>
                <CardDescription>
                  Define what you want to optimize
                </CardDescription>
              </div>
              <Button onClick={addObjective} size="sm" variant="accent" className="gap-2">
                <Plus className="h-4 w-4" />
                Add Objective
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {spec.objectives.map((obj, i) => (
                <ObjectiveEditor
                  key={i}
                  objective={obj}
                  index={i}
                  onChange={(o) => updateObjective(i, o)}
                  onRemove={() => removeObjective(i)}
                />
              ))}
              {spec.objectives.length === 0 && (
                <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
                  No objectives defined. Click "Add Objective" to get started.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Constraints */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-[hsl(var(--warning))]" />
                  Constraints (Optional)
                </CardTitle>
                <CardDescription>
                  Define any constraints on input variables
                </CardDescription>
              </div>
              <Button onClick={addConstraint} size="sm" variant="outline" className="gap-2">
                <Plus className="h-4 w-4" />
                Add Constraint
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {(spec.constraints || []).map((constraint, i) => (
                <ConstraintEditor
                  key={i}
                  constraint={constraint}
                  index={i}
                  inputNames={inputNames}
                  onChange={(c) => updateConstraint(i, c)}
                  onRemove={() => removeConstraint(i)}
                />
              ))}
              {(!spec.constraints || spec.constraints.length === 0) && (
                <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
                  No constraints defined. Constraints are optional.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Strategy */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings2 className="h-5 w-5 text-[hsl(var(--primary))]" />
              Optimization Strategy
            </CardTitle>
            <CardDescription>
              Configure the optimization algorithm
            </CardDescription>
          </CardHeader>
          <CardContent>
            <StrategyEditor
              strategy={spec.strategies.default}
              onChange={updateStrategy}
            />
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="yaml" className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileCode className="h-5 w-5" />
              YAML Specification
            </CardTitle>
            <CardDescription>
              Edit the specification directly in YAML format
            </CardDescription>
          </CardHeader>
          <CardContent>
            {yamlError && (
              <div className="mb-4 p-3 rounded-lg bg-[hsl(var(--destructive))]/10 border border-[hsl(var(--destructive))]/50 text-[hsl(var(--destructive))] text-sm">
                {yamlError}
              </div>
            )}
            <Textarea
              value={yamlStr}
              onChange={(e) => handleYamlChange(e.target.value)}
              className="min-h-[500px] font-mono text-sm"
              placeholder="Enter YAML specification..."
            />
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}





