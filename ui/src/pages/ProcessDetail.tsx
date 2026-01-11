import { useParams, Link, useNavigate } from 'react-router-dom';
import { 
  FlaskConical, 
  ArrowLeft,
  Plus,
  Clock,
  Tag,
  FileCode,
  Target
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useProcess, useCampaigns } from '@/hooks/useApi';
import { formatDate } from '@/lib/utils';

export function ProcessDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: process, isLoading } = useProcess(id!);
  const { data: allCampaigns } = useCampaigns();

  const processCampaigns = allCampaigns?.filter(c => c.process_id === id) || [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[hsl(var(--primary))]" />
      </div>
    );
  }

  if (!process) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Process not found</h2>
        <Button variant="outline" onClick={() => navigate('/processes')} className="mt-4">
          Back to Processes
        </Button>
      </div>
    );
  }

  const spec = process.spec_parsed as Record<string, unknown>;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/processes')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[hsl(var(--primary))]/20 text-[hsl(var(--primary))]">
              <FlaskConical className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">{process.name}</h1>
              <div className="flex items-center gap-3 mt-1">
                <Badge variant="secondary">
                  <Tag className="h-3 w-3 mr-1" />
                  v{process.version}
                </Badge>
                <span className="text-sm text-[hsl(var(--muted-foreground))]">
                  <Clock className="h-3 w-3 inline mr-1" />
                  {formatDate(process.created_at)}
                </span>
              </div>
            </div>
          </div>
        </div>
        <Link to={`/campaigns/new?process=${id}`}>
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            New Campaign
          </Button>
        </Link>
      </div>

      {/* Description */}
      {process.description && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-[hsl(var(--muted-foreground))]">{process.description}</p>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="campaigns">Campaigns ({processCampaigns.length})</TabsTrigger>
          <TabsTrigger value="yaml">YAML</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6 mt-6">
          {/* Inputs */}
          <Card>
            <CardHeader>
              <CardTitle>Inputs</CardTitle>
              <CardDescription>Variables to optimize</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3">
                {(spec.inputs as Array<Record<string, unknown>>)?.map((input, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 rounded-lg border border-[hsl(var(--border))]"
                  >
                    <div>
                      <p className="font-medium">{input.name as string}</p>
                      <p className="text-sm text-[hsl(var(--muted-foreground))]">
                        {input.description as string || 'No description'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{input.type as string}</Badge>
                      {input.bounds && (
                        <span className="text-sm text-[hsl(var(--muted-foreground))]">
                          [{(input.bounds as number[]).join(', ')}]
                        </span>
                      )}
                      {input.values && (
                        <span className="text-sm text-[hsl(var(--muted-foreground))]">
                          {(input.values as string[]).length} options
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Objectives */}
          <Card>
            <CardHeader>
              <CardTitle>Objectives</CardTitle>
              <CardDescription>Metrics to optimize</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3">
                {(spec.objectives as Array<Record<string, unknown>>)?.map((obj, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 rounded-lg border border-[hsl(var(--border))]"
                  >
                    <div>
                      <p className="font-medium">{obj.name as string}</p>
                      <p className="text-sm text-[hsl(var(--muted-foreground))]">
                        {obj.description as string || 'No description'}
                      </p>
                    </div>
                    <Badge variant={obj.direction === 'maximize' ? 'success' : 'destructive'}>
                      {obj.direction as string || (obj.target ? `target: ${obj.target}` : 'minimize')}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Strategy */}
          <Card>
            <CardHeader>
              <CardTitle>Strategy</CardTitle>
              <CardDescription>Optimization configuration</CardDescription>
            </CardHeader>
            <CardContent>
              {Object.entries(spec.strategies as Record<string, Record<string, unknown>> || {}).map(([name, strategy]) => (
                <div key={name} className="p-4 rounded-lg border border-[hsl(var(--border))]">
                  <p className="font-medium mb-3">{name}</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">Sampler</p>
                      <Badge variant="secondary">{strategy.sampler as string}</Badge>
                    </div>
                    <div>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">Model</p>
                      <Badge variant="secondary">{strategy.model as string}</Badge>
                    </div>
                    <div>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">Acquisition</p>
                      <Badge variant="secondary">{strategy.acquisition as string}</Badge>
                    </div>
                    <div>
                      <p className="text-xs text-[hsl(var(--muted-foreground))]">Initial Samples</p>
                      <Badge variant="secondary">{strategy.n_initial as number}</Badge>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="campaigns" className="mt-6">
          {processCampaigns.length === 0 ? (
            <Card className="p-8">
              <div className="flex flex-col items-center justify-center text-center">
                <Target className="h-12 w-12 text-[hsl(var(--muted-foreground))] mb-4" />
                <h3 className="text-lg font-semibold">No campaigns yet</h3>
                <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
                  Start a campaign to begin optimization
                </p>
                <Link to={`/campaigns/new?process=${id}`}>
                  <Button>Create Campaign</Button>
                </Link>
              </div>
            </Card>
          ) : (
            <div className="space-y-4">
              {processCampaigns.map((campaign) => (
                <Link key={campaign.id} to={`/campaigns/${campaign.id}`}>
                  <Card className="hover:border-[hsl(var(--primary))] transition-colors cursor-pointer">
                    <CardContent className="flex items-center justify-between p-4">
                      <div>
                        <p className="font-medium">{campaign.name}</p>
                        <p className="text-sm text-[hsl(var(--muted-foreground))]">
                          {formatDate(campaign.created_at)}
                        </p>
                      </div>
                      <Badge
                        variant={
                          campaign.status === 'active' ? 'success' :
                          campaign.status === 'completed' ? 'default' :
                          campaign.status === 'failed' ? 'destructive' : 'secondary'
                        }
                      >
                        {campaign.status}
                      </Badge>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="yaml" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileCode className="h-5 w-5" />
                YAML Specification
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="p-4 rounded-lg bg-[hsl(var(--muted))] overflow-auto text-sm font-mono">
                {process.spec_yaml}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}





