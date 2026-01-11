import { Link } from 'react-router-dom';
import { 
  FlaskConical, 
  Target, 
  TrendingUp, 
  Activity,
  ArrowRight,
  Sparkles,
  Clock
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useProcesses, useCampaigns, useHealth } from '@/hooks/useApi';
import { formatDate } from '@/lib/utils';

export function Dashboard() {
  const { data: processes, isLoading: loadingProcesses } = useProcesses();
  const { data: campaigns, isLoading: loadingCampaigns } = useCampaigns();
  const { data: health } = useHealth();

  const activeCampaigns = campaigns?.filter(c => c.status === 'active') || [];
  const completedCampaigns = campaigns?.filter(c => c.status === 'completed') || [];
  const recentCampaigns = campaigns?.slice(0, 5) || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-[hsl(var(--muted-foreground))] mt-1">
            Welcome to BOA - Your Bayesian Optimization Assistant
          </p>
        </div>
        <Link to="/processes/new">
          <Button className="gap-2">
            <Sparkles className="h-4 w-4" />
            New Process
          </Button>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Processes</CardTitle>
            <FlaskConical className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loadingProcesses ? '...' : processes?.length || 0}
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Optimization configurations
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Campaigns</CardTitle>
            <Activity className="h-4 w-4 text-[hsl(var(--success))]" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[hsl(var(--success))]">
              {loadingCampaigns ? '...' : activeCampaigns.length}
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Currently running
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <Target className="h-4 w-4 text-[hsl(var(--primary))]" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[hsl(var(--primary))]">
              {loadingCampaigns ? '...' : completedCampaigns.length}
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Finished optimizations
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Server Status</CardTitle>
            <TrendingUp className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <Badge variant={health ? "success" : "destructive"} className="text-sm">
                {health ? "Healthy" : "Offline"}
              </Badge>
            </div>
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              API Status
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Recent Campaigns */}
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Recent Campaigns</CardTitle>
            <CardDescription>
              Your latest optimization campaigns
            </CardDescription>
          </CardHeader>
          <CardContent>
            {recentCampaigns.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Target className="h-12 w-12 text-[hsl(var(--muted-foreground))] mb-4" />
                <h3 className="text-lg font-semibold">No campaigns yet</h3>
                <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
                  Create a process and start your first optimization campaign
                </p>
                <Link to="/processes/new">
                  <Button variant="outline">Create Process</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {recentCampaigns.map((campaign) => (
                  <Link
                    key={campaign.id}
                    to={`/campaigns/${campaign.id}`}
                    className="flex items-center justify-between p-4 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--secondary))] transition-colors"
                  >
                    <div className="space-y-1">
                      <p className="font-medium">{campaign.name}</p>
                      <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
                        <Clock className="h-3 w-3" />
                        {formatDate(campaign.created_at)}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge
                        variant={
                          campaign.status === 'active' ? 'success' :
                          campaign.status === 'completed' ? 'default' :
                          campaign.status === 'failed' ? 'destructive' : 'secondary'
                        }
                      >
                        {campaign.status}
                      </Badge>
                      <ArrowRight className="h-4 w-4 text-[hsl(var(--muted-foreground))]" />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Start */}
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Quick Start</CardTitle>
            <CardDescription>
              Start optimizing with pre-built templates
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Link
              to="/processes/new?template=ald"
              className="flex items-center gap-4 p-4 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))]/10 hover:border-[hsl(var(--accent))] transition-all group"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[hsl(var(--accent))]/20 text-[hsl(var(--accent))]">
                <FlaskConical className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <p className="font-medium group-hover:text-[hsl(var(--accent))]">ALD Parameters</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Atomic Layer Deposition optimization
                </p>
              </div>
              <ArrowRight className="h-4 w-4 text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--accent))] group-hover:translate-x-1 transition-all" />
            </Link>

            <Link
              to="/processes/new?template=spincoating"
              className="flex items-center gap-4 p-4 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--primary))]/10 hover:border-[hsl(var(--primary))] transition-all group"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[hsl(var(--primary))]/20 text-[hsl(var(--primary))]">
                <Activity className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <p className="font-medium group-hover:text-[hsl(var(--primary))]">Spin Coating</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Film thickness & uniformity
                </p>
              </div>
              <ArrowRight className="h-4 w-4 text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--primary))] group-hover:translate-x-1 transition-all" />
            </Link>

            <Link
              to="/processes/new?template=perovskite"
              className="flex items-center gap-4 p-4 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--warning))]/10 hover:border-[hsl(var(--warning))] transition-all group"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[hsl(var(--warning))]/20 text-[hsl(var(--warning))]">
                <Sparkles className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <p className="font-medium group-hover:text-[hsl(var(--warning))]">Perovskite Stability</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  Degradation optimization
                </p>
              </div>
              <ArrowRight className="h-4 w-4 text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--warning))] group-hover:translate-x-1 transition-all" />
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}





