import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from '@/components/layouts/MainLayout';
import Home from '@/pages/Home';
import Options from '@/pages/Options';
import Pricing from '@/pages/Pricing';
import Profile from '@/pages/Profile';
import Login from '@/pages/Login';
import ResetPassword from '@/pages/ResetPassword';
import NewLanding from '@/pages/NewLanding';
import Landing from '@/pages/Landing';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/" element={<NewLanding />} />
        <Route path="/landing-old" element={<Landing />} />
        <Route element={<MainLayout />}>
          <Route path="/stock" element={<Home />} />
          <Route path="/options" element={<Options />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
