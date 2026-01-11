import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Target, 
  ArrowLeft,
  Play,
  Plus,
  Activity,
  TrendingUp,
  Pause,
  CheckCircle,
  RefreshCw,
  Eye,
  BarChart3,
  Table as TableIcon,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  useCampaign, 
  useProcess, 
  useObservations, 
  useIterations, 
  useCampaignMetrics, 
  usePropose, 
  useCreateObservation,
  useUpdateCampaign
} from '@/hooks/useApi';
import { formatDate, formatNumber } from '@/lib/utils';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts';

export function CampaignDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const { data: campaign, isLoading: loadingCampaign } = useCampaign(id!);
  const { data: process } = useProcess(campaign?.process_id || '');
  const { data: observations } = useObservations(id!);
  const { data: iterations } = useIterations(id!);
  const { data: metrics, refetch: refetchMetrics } = useCampaignMetrics(id!);
  
  const proposeMutation = usePropose(id!);
  const createObservation = useCreateObservation(id!);
  const updateCampaign = useUpdateCampaign();
  
  const [nCandidates, setNCandidates] = useState(1);
  const [lastProposal, setLastProposal] = useState<Array<Record<string, unknown>> | null>(null);
  const [observeDialogOpen, setObserveDialogOpen] = useState(false);
  const [observeData, setObserveData] = useState<{ inputs: Record<string, unknown>; outputs: Record<string, string> }>({ inputs: {}, outputs: {} });

  if (loadingCampaign) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[hsl(var(--primary))]" />
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Campaign not found</h2>
        <Button variant="outline" onClick={() => navigate('/campaigns')} className="mt-4">
          Back to Campaigns
        </Button>
      </div>
    );
  }

  const spec = process?.spec_parsed as Record<string, unknown> | undefined;
  const inputs = (spec?.inputs as Array<Record<string, unknown>>) || [];
  const objectives = (spec?.objectives as Array<Record<string, unknown>>) || [];

  const handlePropose = async () => {
    try {
      const result = await proposeMutation.mutateAsync(nCandidates);
      setLastProposal(result.candidates);
      refetchMetrics();
    } catch (error) {
      console.error('Failed to propose:', error);
      alert(error instanceof Error ? error.message : 'Failed to generate proposals');
    }
  };

  const handleObserve = async () => {
    try {
      const y_raw: Record<string, number> = {};
      for (const [key, value] of Object.entries(observeData.outputs)) {
        y_raw[key] = parseFloat(value);
      }
      await createObservation.mutateAsync({
        x_raw: observeData.inputs,
        y_raw,
      });
      setObserveDialogOpen(false);
      setObserveData({ inputs: {}, outputs: {} });
      refetchMetrics();
    } catch (error) {
      console.error('Failed to record observation:', error);
      alert(error instanceof Error ? error.message : 'Failed to record observation');
    }
  };

  const handleStatusChange = async (status: string) => {
    try {
      await updateCampaign.mutateAsync({ id: id!, data: { status } });
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  };

  // Prepare Pareto front data for chart
  const paretoData = metrics?.pareto_front?.map((point, i) => ({
    x: point[0],
    y: point[1],
    name: `Point ${i + 1}`,
  })) || [];

  // Prepare observations for scatter plot
  const objNames = objectives?.map(o => o.name as string) || [];
  const obsData = (objNames.length >= 2 && observations && observations.length > 0) 
    ? observations.map((obs, i) => {
        const y = (obs.y_raw || {}) as Record<string, number>;
        const obj1 = objNames[0];
        const obj2 = objNames[1];
        return {
          x: obj1 && y[obj1] != null ? y[obj1] : 0,
          y: obj2 && y[obj2] != null ? y[obj2] : 0,
          name: `Obs ${i + 1}`,
        };
      }) 
    : [];

  // Hypervolume over time (mock - would need iteration-level metrics)
  const hvData = iterations?.map((iter, i) => ({
    iteration: i + 1,
    hypervolume: (iter.metrics as Record<string, number>)?.hypervolume ?? null,
  })).filter(d => d.hypervolume !== null) || [];

  const statusColors: Record<string, "success" | "default" | "destructive" | "secondary" | "warning"> = {
    active: 'success',
    completed: 'default',
    failed: 'destructive',
    paused: 'warning',
    draft: 'secondary',
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/campaigns')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[hsl(var(--primary))]/20 text-[hsl(var(--primary))]">
              {campaign.status === 'active' ? (
                <Activity className="h-6 w-6 animate-pulse" />
              ) : (
                <Target className="h-6 w-6" />
              )}
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">{campaign.name}</h1>
              <div className="flex items-center gap-3 mt-1">
                <Badge variant={statusColors[campaign.status] || 'secondary'}>
                  {campaign.status}
                </Badge>
                <span className="text-sm text-[hsl(var(--muted-foreground))]">
                  {process?.name}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {campaign.status === 'draft' && (
            <Button variant="default" onClick={() => handleStatusChange('active')} className="gap-2">
              <Play className="h-4 w-4" />
              Start
            </Button>
          )}
          {campaign.status === 'active' && (
            <>
              <Button variant="outline" onClick={() => handleStatusChange('paused')} className="gap-2">
                <Pause className="h-4 w-4" />
                Pause
              </Button>
              <Button variant="default" onClick={() => handleStatusChange('completed')} className="gap-2">
                <CheckCircle className="h-4 w-4" />
                Complete
              </Button>
            </>
          )}
          {campaign.status === 'paused' && (
            <Button variant="default" onClick={() => handleStatusChange('active')} className="gap-2">
              <Play className="h-4 w-4" />
              Resume
            </Button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Observations</CardTitle>
            <Eye className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{observations?.length || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Iterations</CardTitle>
            <RefreshCw className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{iterations?.length || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pareto Size</CardTitle>
            <TrendingUp className="h-4 w-4 text-[hsl(var(--primary))]" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[hsl(var(--primary))]">
              {metrics?.pareto_front_size || 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Hypervolume</CardTitle>
            <BarChart3 className="h-4 w-4 text-[hsl(var(--accent))]" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[hsl(var(--accent))]">
              {metrics?.hypervolume != null ? formatNumber(metrics.hypervolume, 2) : '—'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Action Panel */}
      <Card className="border-[hsl(var(--primary))]/50 bg-[hsl(var(--primary))]/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-[hsl(var(--primary))]" />
            Campaign Actions
          </CardTitle>
          <CardDescription>
            Execute optimization steps
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {/* Propose */}
            <div className="flex items-center gap-2">
              <Label htmlFor="n-candidates" className="whitespace-nowrap">Candidates:</Label>
              <Input
                id="n-candidates"
                type="number"
                min={1}
                max={10}
                value={nCandidates}
                onChange={(e) => setNCandidates(parseInt(e.target.value) || 1)}
                className="w-20"
              />
              <Button 
                onClick={handlePropose} 
                disabled={proposeMutation.isPending}
                className="gap-2"
              >
                {proposeMutation.isPending ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Propose Next
              </Button>
            </div>

            {/* Observe */}
            <Dialog open={observeDialogOpen} onOpenChange={setObserveDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="gap-2">
                  <Plus className="h-4 w-4" />
                  Record Observation
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Record Observation</DialogTitle>
                  <DialogDescription>
                    Enter the input values and observed outputs
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-6 py-4">
                  {/* Inputs */}
                  <div>
                    <h4 className="font-medium mb-3">Inputs</h4>
                    <div className="grid gap-3">
                      {inputs.map((input) => (
                        <div key={input.name as string} className="flex items-center gap-4">
                          <Label className="w-32 text-right">{input.name as string}</Label>
                          <Input
                            type={input.type === 'categorical' ? 'text' : 'number'}
                            value={(observeData.inputs[input.name as string] as string) || ''}
                            onChange={(e) => setObserveData(prev => ({
                              ...prev,
                              inputs: { ...prev.inputs, [input.name as string]: input.type === 'categorical' ? e.target.value : parseFloat(e.target.value) }
                            }))}
                            placeholder={`Enter ${input.name}`}
                            className="flex-1"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                  {/* Outputs */}
                  <div>
                    <h4 className="font-medium mb-3">Outputs</h4>
                    <div className="grid gap-3">
                      {objectives.map((obj) => (
                        <div key={obj.name as string} className="flex items-center gap-4">
                          <Label className="w-32 text-right">{obj.name as string}</Label>
                          <Input
                            type="number"
                            step="any"
                            value={observeData.outputs[obj.name as string] || ''}
                            onChange={(e) => setObserveData(prev => ({
                              ...prev,
                              outputs: { ...prev.outputs, [obj.name as string]: e.target.value }
                            }))}
                            placeholder={`Enter ${obj.name}`}
                            className="flex-1"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setObserveDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleObserve} disabled={createObservation.isPending}>
                    {createObservation.isPending ? 'Recording...' : 'Record'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            {/* Refresh Metrics */}
            <Button variant="ghost" onClick={() => refetchMetrics()} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>

          {/* Last Proposal */}
          {lastProposal && lastProposal.length > 0 && (
            <div className="mt-6 p-4 rounded-lg bg-[hsl(var(--card))] border border-[hsl(var(--border))]">
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <Zap className="h-4 w-4 text-[hsl(var(--warning))]" />
                Suggested Next Experiment{lastProposal.length > 1 ? 's' : ''}
              </h4>
              <div className="space-y-3">
                {lastProposal.map((candidate, i) => (
                  <div key={i} className="p-3 rounded border border-[hsl(var(--border))] bg-[hsl(var(--muted))]/50">
                    <p className="text-sm font-medium mb-2">Candidate {i + 1}</p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      {Object.entries(candidate).map(([key, value]) => (
                        <div key={key} className="text-sm">
                          <span className="text-[hsl(var(--muted-foreground))]">{key}: </span>
                          <span className="font-mono">
                            {typeof value === 'number' ? formatNumber(value, 3) : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="mt-2"
                      onClick={() => {
                        setObserveData({ inputs: candidate as Record<string, unknown>, outputs: {} });
                        setObserveDialogOpen(true);
                      }}
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      Use These Values
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs defaultValue="visualizations">
        <TabsList>
          <TabsTrigger value="visualizations" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            Visualizations
          </TabsTrigger>
          <TabsTrigger value="observations" className="gap-2">
            <TableIcon className="h-4 w-4" />
            Observations ({observations?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="iterations" className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Iterations ({iterations?.length || 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="visualizations" className="mt-6 space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Pareto Front */}
            <Card>
              <CardHeader>
                <CardTitle>Pareto Front</CardTitle>
                <CardDescription>
                  Non-dominated solutions
                </CardDescription>
              </CardHeader>
              <CardContent>
                {paretoData.length > 0 || obsData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis 
                        type="number" 
                        dataKey="x" 
                        name={objectives[0]?.name as string || 'Objective 1'}
                        stroke="hsl(var(--muted-foreground))"
                        tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      />
                      <YAxis 
                        type="number" 
                        dataKey="y" 
                        name={objectives[1]?.name as string || 'Objective 2'}
                        stroke="hsl(var(--muted-foreground))"
                        tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px'
                        }}
                      />
                      <Legend />
                      <Scatter 
                        name="All Observations" 
                        data={obsData} 
                        fill="hsl(var(--muted-foreground))"
                        opacity={0.5}
                      />
                      <Scatter 
                        name="Pareto Front" 
                        data={paretoData} 
                        fill="hsl(var(--primary))"
                      />
                    </ScatterChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-[300px] text-[hsl(var(--muted-foreground))]">
                    No data yet. Add observations to see the Pareto front.
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Hypervolume Progress */}
            <Card>
              <CardHeader>
                <CardTitle>Optimization Progress</CardTitle>
                <CardDescription>
                  Hypervolume indicator over iterations
                </CardDescription>
              </CardHeader>
              <CardContent>
                {hvData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={hvData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis 
                        dataKey="iteration" 
                        stroke="hsl(var(--muted-foreground))"
                        tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      />
                      <YAxis 
                        stroke="hsl(var(--muted-foreground))"
                        tick={{ fill: 'hsl(var(--muted-foreground))' }}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px'
                        }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="hypervolume" 
                        stroke="hsl(var(--accent))"
                        strokeWidth={2}
                        dot={{ fill: 'hsl(var(--accent))' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-[300px] text-[hsl(var(--muted-foreground))]">
                    Run more iterations to see progress.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="observations" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Observations</CardTitle>
              <CardDescription>
                All recorded experimental results
              </CardDescription>
            </CardHeader>
            <CardContent>
              {observations && observations.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      {inputs.slice(0, 4).map((input) => (
                        <TableHead key={input.name as string}>{input.name as string}</TableHead>
                      ))}
                      {objectives.map((obj) => (
                        <TableHead key={obj.name as string} className="text-[hsl(var(--primary))]">
                          {obj.name as string}
                        </TableHead>
                      ))}
                      <TableHead>Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {observations.map((obs, i) => (
                      <TableRow key={obs.id}>
                        <TableCell className="font-medium">{i + 1}</TableCell>
                        {inputs.slice(0, 4).map((input) => {
                          const xRaw = (obs.x_raw || {}) as Record<string, unknown>;
                          const value = xRaw[input.name as string];
                          return (
                            <TableCell key={input.name as string} className="font-mono text-sm">
                              {typeof value === 'number' ? formatNumber(value, 3) : String(value ?? '—')}
                            </TableCell>
                          );
                        })}
                        {objectives.map((obj) => {
                          const yRaw = (obs.y_raw || {}) as Record<string, number>;
                          const value = yRaw[obj.name as string];
                          return (
                            <TableCell key={obj.name as string} className="font-mono text-sm text-[hsl(var(--primary))]">
                              {value != null ? formatNumber(value, 4) : '—'}
                            </TableCell>
                          );
                        })}
                        <TableCell className="text-[hsl(var(--muted-foreground))]">
                          {formatDate(obs.created_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Eye className="h-12 w-12 text-[hsl(var(--muted-foreground))] mb-4" />
                  <h3 className="text-lg font-semibold">No observations yet</h3>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    Record your first observation to start tracking results
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="iterations" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Iterations</CardTitle>
              <CardDescription>
                Optimization iteration history
              </CardDescription>
            </CardHeader>
            <CardContent>
              {iterations && iterations.length > 0 ? (
                <div className="space-y-4">
                  {iterations.map((iter) => (
                    <div 
                      key={iter.id} 
                      className="p-4 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))]/50"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <Badge variant="secondary">Iteration {iter.index + 1}</Badge>
                          <span className="text-sm text-[hsl(var(--muted-foreground))]">
                            {formatDate(iter.created_at)}
                          </span>
                        </div>
                      </div>
                      {iter.metrics && Object.keys(iter.metrics as object).length > 0 && (
                        <div className="grid grid-cols-3 gap-4 mt-3">
                          {Object.entries(iter.metrics as Record<string, unknown>).map(([key, value]) => (
                            <div key={key} className="text-sm">
                              <span className="text-[hsl(var(--muted-foreground))]">{key}: </span>
                              <span className="font-mono">
                                {typeof value === 'number' ? formatNumber(value, 4) : String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <RefreshCw className="h-12 w-12 text-[hsl(var(--muted-foreground))] mb-4" />
                  <h3 className="text-lg font-semibold">No iterations yet</h3>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    Click "Propose Next" to start the optimization
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

