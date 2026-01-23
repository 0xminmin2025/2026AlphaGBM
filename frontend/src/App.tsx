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
import { AnalyticsProvider } from '@/components/analytics/AnalyticsProvider';

function App() {
  return (
    <HelmetProvider>
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
            </Route>
          </Routes>
        </AnalyticsProvider>
      </BrowserRouter>
    </HelmetProvider>
  );
}

export default App;
