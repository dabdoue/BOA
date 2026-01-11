import { Link } from 'react-router-dom';
import { 
  Target, 
  Plus, 
  ChevronRight,
  Clock,
  Activity
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useCampaigns, useProcesses } from '@/hooks/useApi';
import { formatDate } from '@/lib/utils';

export function Campaigns() {
  const { data: campaigns, isLoading } = useCampaigns();
  const { data: processes } = useProcesses();

  const getProcessName = (processId: string) => {
    return processes?.find(p => p.id === processId)?.name || 'Unknown Process';
  };

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
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Campaigns</h1>
          <p className="text-[hsl(var(--muted-foreground))] mt-1">
            Monitor and control your optimization campaigns
          </p>
        </div>
        <Link to="/campaigns/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            New Campaign
          </Button>
        </Link>
      </div>

      {/* Campaign List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-6 bg-[hsl(var(--muted))] rounded w-1/3 mb-4" />
                <div className="h-4 bg-[hsl(var(--muted))] rounded w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : campaigns?.length === 0 ? (
        <Card className="p-12">
          <div className="flex flex-col items-center justify-center text-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[hsl(var(--primary))]/10 mb-6">
              <Target className="h-10 w-10 text-[hsl(var(--primary))]" />
            </div>
            <h3 className="text-xl font-semibold mb-2">No campaigns yet</h3>
            <p className="text-[hsl(var(--muted-foreground))] mb-6 max-w-md">
              Campaigns are instances of optimization runs. Create a process first, then start a campaign.
            </p>
            <Link to="/processes">
              <Button size="lg" className="gap-2">
                <Plus className="h-5 w-5" />
                View Processes
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {campaigns?.map((campaign) => (
            <Link key={campaign.id} to={`/campaigns/${campaign.id}`}>
              <Card className="hover:border-[hsl(var(--primary))] hover:shadow-lg hover:shadow-[hsl(var(--primary))]/10 transition-all cursor-pointer group">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[hsl(var(--primary))]/20 text-[hsl(var(--primary))]">
                        {campaign.status === 'active' ? (
                          <Activity className="h-6 w-6 animate-pulse" />
                        ) : (
                          <Target className="h-6 w-6" />
                        )}
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold group-hover:text-[hsl(var(--primary))] transition-colors">
                          {campaign.name}
                        </h3>
                        <div className="flex items-center gap-3 mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                          <span>{getProcessName(campaign.process_id)}</span>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDate(campaign.created_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <Badge variant={statusColors[campaign.status] || 'secondary'}>
                        {campaign.status}
                      </Badge>
                      <ChevronRight className="h-5 w-5 text-[hsl(var(--muted-foreground))] group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                  {campaign.description && (
                    <p className="mt-4 text-sm text-[hsl(var(--muted-foreground))] line-clamp-2">
                      {campaign.description}
                    </p>
                  )}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}





