import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  Target, 
  ArrowLeft,
  Save,
  FlaskConical,
  Settings2,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useProcesses, useProcess, useCreateCampaign } from '@/hooks/useApi';

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

export function CampaignNew() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectedProcess = searchParams.get('process');

  const { data: processes, isLoading: loadingProcesses } = useProcesses();
  const createCampaign = useCreateCampaign();

  const [processId, setProcessId] = useState(preselectedProcess || '');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  // Strategy overrides
  const [overrideSampler, setOverrideSampler] = useState(false);
  const [sampler, setSampler] = useState('lhs');
  const [overrideModel, setOverrideModel] = useState(false);
  const [model, setModel] = useState('gp_matern');
  const [overrideAcquisition, setOverrideAcquisition] = useState(false);
  const [acquisition, setAcquisition] = useState('random');
  const [overrideNInitial, setOverrideNInitial] = useState(false);
  const [nInitial, setNInitial] = useState(5);

  const { data: selectedProcess } = useProcess(processId);

  useEffect(() => {
    if (preselectedProcess) {
      setProcessId(preselectedProcess);
    }
  }, [preselectedProcess]);

  useEffect(() => {
    if (processId && processes) {
      const process = processes.find(p => p.id === processId);
      if (process && !name) {
        setName(`${process.name} - Campaign ${new Date().toLocaleDateString()}`);
      }
    }
  }, [processId, processes, name]);

  // Load default strategy from process
  useEffect(() => {
    if (selectedProcess?.spec_parsed) {
      const spec = selectedProcess.spec_parsed as { strategies?: { default?: { sampler?: string; model?: string; acquisition?: string; n_initial?: number } } };
      const defaultStrategy = spec.strategies?.default;
      if (defaultStrategy) {
        if (defaultStrategy.sampler) setSampler(defaultStrategy.sampler);
        if (defaultStrategy.model) setModel(defaultStrategy.model);
        if (defaultStrategy.acquisition) setAcquisition(defaultStrategy.acquisition);
        if (defaultStrategy.n_initial) setNInitial(defaultStrategy.n_initial);
      }
    }
  }, [selectedProcess]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Build strategy config with overrides
    const strategyConfig: Record<string, unknown> = {};
    if (overrideSampler) strategyConfig.sampler = sampler;
    if (overrideModel) strategyConfig.model = model;
    if (overrideAcquisition) strategyConfig.acquisition = acquisition;
    if (overrideNInitial) strategyConfig.n_initial = nInitial;

    try {
      const campaign = await createCampaign.mutateAsync({
        process_id: processId,
        name,
        description: description || undefined,
        strategy_config: Object.keys(strategyConfig).length > 0 ? strategyConfig : undefined,
      });
      navigate(`/campaigns/${campaign.id}`);
    } catch (error) {
      console.error('Failed to create campaign:', error);
      alert(error instanceof Error ? error.message : 'Failed to create campaign');
    }
  };

  // Get process info for display
  const processSpec = selectedProcess?.spec_parsed as { 
    inputs?: Array<{ name: string; type: string }>; 
    objectives?: Array<{ name: string; direction?: string }>;
    strategies?: { default?: { sampler?: string; model?: string; acquisition?: string; n_initial?: number } }
  } | undefined;

  return (
    <div className="space-y-8 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">New Campaign</h1>
          <p className="text-[hsl(var(--muted-foreground))] mt-1">
            Start a new optimization campaign
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Process Selection */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-5 w-5 text-[hsl(var(--primary))]" />
              Select Process
            </CardTitle>
            <CardDescription>
              Choose the optimization specification to use
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="process">Process</Label>
              <Select value={processId} onValueChange={setProcessId} required>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={loadingProcesses ? "Loading..." : "Select a process"} />
                </SelectTrigger>
                <SelectContent>
                  {processes?.map((process) => (
                    <SelectItem key={process.id} value={process.id}>
                      <div className="flex items-center gap-2">
                        <FlaskConical className="h-4 w-4" />
                        <span>{process.name}</span>
                        <Badge variant="secondary" className="text-xs">v{process.version}</Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Process Preview */}
            {selectedProcess && processSpec && (
              <div className="p-4 rounded-lg bg-[hsl(var(--muted))] border border-[hsl(var(--border))]">
                <h4 className="font-medium mb-3">Process Overview</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-[hsl(var(--muted-foreground))]">Inputs</p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {processSpec.inputs?.slice(0, 5).map((inp, i) => (
                        <Badge key={i} variant="outline" className="text-xs">
                          {inp.name}
                        </Badge>
                      ))}
                      {(processSpec.inputs?.length || 0) > 5 && (
                        <Badge variant="secondary" className="text-xs">
                          +{(processSpec.inputs?.length || 0) - 5} more
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div>
                    <p className="text-[hsl(var(--muted-foreground))]">Objectives</p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {processSpec.objectives?.map((obj, i) => (
                        <Badge 
                          key={i} 
                          variant={obj.direction === 'maximize' ? 'success' : 'destructive'}
                          className="text-xs"
                        >
                          {obj.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Campaign Details */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-[hsl(var(--accent))]" />
              Campaign Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Campaign Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter campaign name"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the purpose of this campaign..."
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* Strategy Configuration */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="h-5 w-5 text-[hsl(var(--primary))]" />
                  Strategy Configuration
                </CardTitle>
                <CardDescription>
                  Override default strategy settings for this campaign
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="gap-2"
              >
                {showAdvanced ? 'Hide' : 'Show'} Options
                {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
          </CardHeader>
          
          {showAdvanced && (
            <CardContent className="space-y-6">
              {/* Default values from process */}
              {processSpec?.strategies?.default && (
                <div className="p-3 rounded-lg bg-[hsl(var(--muted))] text-sm">
                  <p className="text-[hsl(var(--muted-foreground))] mb-2">Default from process:</p>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">Sampler: {processSpec.strategies.default.sampler}</Badge>
                    <Badge variant="secondary">Model: {processSpec.strategies.default.model}</Badge>
                    <Badge variant="secondary">Acquisition: {processSpec.strategies.default.acquisition}</Badge>
                    <Badge variant="secondary">Initial: {processSpec.strategies.default.n_initial}</Badge>
                  </div>
                </div>
              )}

              {/* Sampler Override */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Sampler</Label>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      Method for generating initial samples
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant={overrideSampler ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setOverrideSampler(!overrideSampler)}
                  >
                    {overrideSampler ? 'Custom' : 'Use Default'}
                  </Button>
                </div>
                {overrideSampler && (
                  <Select value={sampler} onValueChange={setSampler}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SAMPLERS.map(s => (
                        <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              {/* Model Override */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Surrogate Model</Label>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      Model used to predict outcomes
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant={overrideModel ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setOverrideModel(!overrideModel)}
                  >
                    {overrideModel ? 'Custom' : 'Use Default'}
                  </Button>
                </div>
                {overrideModel && (
                  <Select value={model} onValueChange={setModel}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MODELS.map(m => (
                        <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              {/* Acquisition Override */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Acquisition Function</Label>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      Strategy for selecting next experiments
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant={overrideAcquisition ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setOverrideAcquisition(!overrideAcquisition)}
                  >
                    {overrideAcquisition ? 'Custom' : 'Use Default'}
                  </Button>
                </div>
                {overrideAcquisition && (
                  <Select value={acquisition} onValueChange={setAcquisition}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ACQUISITIONS.map(a => (
                        <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              {/* Initial Samples Override */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Initial Samples</Label>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      Number of random samples before model-guided
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant={overrideNInitial ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setOverrideNInitial(!overrideNInitial)}
                  >
                    {overrideNInitial ? 'Custom' : 'Use Default'}
                  </Button>
                </div>
                {overrideNInitial && (
                  <Input
                    type="number"
                    min={1}
                    max={100}
                    value={nInitial}
                    onChange={(e) => setNInitial(parseInt(e.target.value) || 5)}
                  />
                )}
              </div>
            </CardContent>
          )}
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-4">
          <Button type="button" variant="outline" onClick={() => navigate(-1)}>
            Cancel
          </Button>
          <Button 
            type="submit" 
            disabled={createCampaign.isPending || !processId} 
            className="gap-2"
          >
            <Save className="h-4 w-4" />
            {createCampaign.isPending ? 'Creating...' : 'Create Campaign'}
          </Button>
        </div>
      </form>
    </div>
  );
}
