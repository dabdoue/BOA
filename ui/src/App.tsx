import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from '@/components/Layout';
import { Dashboard } from '@/pages/Dashboard';
import { Processes } from '@/pages/Processes';
import { ProcessNew } from '@/pages/ProcessNew';
import { ProcessDetail } from '@/pages/ProcessDetail';
import { Campaigns } from '@/pages/Campaigns';
import { CampaignNew } from '@/pages/CampaignNew';
import { CampaignDetail } from '@/pages/CampaignDetail';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="processes" element={<Processes />} />
            <Route path="processes/new" element={<ProcessNew />} />
            <Route path="processes/:id" element={<ProcessDetail />} />
            <Route path="campaigns" element={<Campaigns />} />
            <Route path="campaigns/new" element={<CampaignNew />} />
            <Route path="campaigns/:id" element={<CampaignDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
