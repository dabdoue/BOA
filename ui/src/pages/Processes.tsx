import { Link } from 'react-router-dom';
import { 
  FlaskConical, 
  Plus, 
  Trash2,
  ChevronRight,
  Clock,
  Tag
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useProcesses, useDeleteProcess } from '@/hooks/useApi';
import { formatDate } from '@/lib/utils';

export function Processes() {
  const { data: processes, isLoading } = useProcesses();
  const deleteProcess = useDeleteProcess();

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this process?')) {
      deleteProcess.mutate(id);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Processes</h1>
          <p className="text-[hsl(var(--muted-foreground))] mt-1">
            Define optimization specifications for your experiments
          </p>
        </div>
        <Link to="/processes/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            New Process
          </Button>
        </Link>
      </div>

      {/* Process Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-6 bg-[hsl(var(--muted))] rounded w-3/4" />
                <div className="h-4 bg-[hsl(var(--muted))] rounded w-1/2 mt-2" />
              </CardHeader>
              <CardContent>
                <div className="h-4 bg-[hsl(var(--muted))] rounded w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : processes?.length === 0 ? (
        <Card className="p-12">
          <div className="flex flex-col items-center justify-center text-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[hsl(var(--primary))]/10 mb-6">
              <FlaskConical className="h-10 w-10 text-[hsl(var(--primary))]" />
            </div>
            <h3 className="text-xl font-semibold mb-2">No processes yet</h3>
            <p className="text-[hsl(var(--muted-foreground))] mb-6 max-w-md">
              Processes define the optimization problem: inputs, objectives, and strategies.
              Create your first process to get started.
            </p>
            <Link to="/processes/new">
              <Button size="lg" className="gap-2">
                <Plus className="h-5 w-5" />
                Create Your First Process
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {processes?.map((process) => (
            <Link key={process.id} to={`/processes/${process.id}`}>
              <Card className="h-full hover:border-[hsl(var(--primary))] hover:shadow-lg hover:shadow-[hsl(var(--primary))]/10 transition-all cursor-pointer group">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[hsl(var(--primary))]/20 text-[hsl(var(--primary))]">
                        <FlaskConical className="h-5 w-5" />
                      </div>
                      <div>
                        <CardTitle className="text-lg group-hover:text-[hsl(var(--primary))] transition-colors">
                          {process.name}
                        </CardTitle>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="secondary" className="text-xs">
                            <Tag className="h-3 w-3 mr-1" />
                            v{process.version}
                          </Badge>
                          {process.is_active && (
                            <Badge variant="success" className="text-xs">Active</Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => handleDelete(process.id, e)}
                    >
                      <Trash2 className="h-4 w-4 text-[hsl(var(--destructive))]" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="line-clamp-2 mb-4">
                    {process.description || 'No description provided'}
                  </CardDescription>
                  <div className="flex items-center justify-between text-xs text-[hsl(var(--muted-foreground))]">
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDate(process.created_at)}
                    </div>
                    <ChevronRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}





