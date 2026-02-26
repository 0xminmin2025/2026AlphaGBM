import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import MainLayout from '@/components/layouts/MainLayout';
import Home from '@/pages/Home';
import Options from '@/pages/Options';
import ReverseScore from '@/pages/ReverseScore';
import Pricing from '@/pages/Pricing';
import Profile from '@/pages/Profile';
import Login from '@/pages/Login';
import ResetPassword from '@/pages/ResetPassword';
import NewLanding from '@/pages/NewLanding';
import Landing from '@/pages/Landing';
import KnowledgeBasePage from '@/pages/knowledge-base/KnowledgeBasePage';
import { AnalyticsProvider } from '@/components/analytics/AnalyticsProvider';
import { ToastProvider } from '@/components/ui/toast';

function App() {
  return (
    <HelmetProvider>
      <ToastProvider>
        <BrowserRouter>
          <AnalyticsProvider>
            <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/" element={<NewLanding />} />
            <Route path="/landing-old" element={<Landing />} />
            <Route element={<MainLayout />}>
              <Route path="/stock" element={<Home />} />
              <Route path="/options" element={<Options />} />
              <Route path="/options/reverse" element={<ReverseScore />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/knowledge" element={<KnowledgeBasePage />} />
              <Route path="/knowledge/:chapterSlug" element={<KnowledgeBasePage />} />
            </Route>
          </Routes>
          </AnalyticsProvider>
        </BrowserRouter>
      </ToastProvider>
    </HelmetProvider>
  );
}

export default App;
