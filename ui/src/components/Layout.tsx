import { Link, Outlet, useLocation } from 'react-router-dom';
import { 
  FlaskConical, 
  LayoutDashboard, 
  Beaker, 
  Target, 
  Activity,
  Settings,
  ChevronRight,
  Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useHealth } from '@/hooks/useApi';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Processes', href: '/processes', icon: FlaskConical },
  { name: 'Campaigns', href: '/campaigns', icon: Target },
];

export function Layout() {
  const location = useLocation();
  const { data: health, isError } = useHealth();

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[hsl(var(--background))] bg-grid bg-gradient-radial">
        {/* Sidebar */}
        <aside className="fixed inset-y-0 left-0 z-50 w-64 border-r border-[hsl(var(--border))] bg-[hsl(var(--card))]/80 backdrop-blur-xl">
          {/* Logo */}
          <div className="flex h-16 items-center gap-3 px-6 border-b border-[hsl(var(--border))]">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[hsl(var(--primary))] glow-primary">
              <Beaker className="h-5 w-5 text-[hsl(var(--primary-foreground))]" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">BOA</h1>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">Bayesian Optimization</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex flex-col gap-1 p-4">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href || 
                (item.href !== '/' && location.pathname.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                    isActive
                      ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-lg shadow-[hsl(var(--primary))]/20"
                      : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--secondary))] hover:text-[hsl(var(--foreground))]"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {item.name}
                  {isActive && <ChevronRight className="ml-auto h-4 w-4" />}
                </Link>
              );
            })}
          </nav>

          <Separator />

          {/* Quick Actions */}
          <div className="p-4">
            <p className="px-3 text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] mb-2">
              Quick Actions
            </p>
            <Link
              to="/processes/new"
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--accent))]/20 hover:text-[hsl(var(--accent))] transition-all"
            >
              <Zap className="h-5 w-5" />
              New Process
            </Link>
          </div>

          {/* Status */}
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-[hsl(var(--border))]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className={cn(
                  "h-4 w-4",
                  health && !isError ? "text-[hsl(var(--success))]" : "text-[hsl(var(--destructive))]"
                )} />
                <span className="text-sm text-[hsl(var(--muted-foreground))]">Server</span>
              </div>
              <Badge variant={health && !isError ? "success" : "destructive"}>
                {health && !isError ? "Online" : "Offline"}
              </Badge>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="pl-64">
          <div className="min-h-screen p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}





