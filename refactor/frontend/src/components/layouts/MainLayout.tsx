import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/components/auth/AuthProvider';
import { LanguageToggle } from '../ui/language-toggle';

export default function MainLayout() {
    const { user, signOut } = useAuth();
    const navigate = useNavigate();

    const handleLogout = async () => {
        await signOut();
        navigate('/login');
    };

    return (
        <div className="min-h-screen bg-[#09090B] text-[#FAFAFA] flex flex-col font-sans">
            {/* Navbar - Styled to match original base.html / landing nav */}
            <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-[#09090B]/80 backdrop-blur-md">
                <div className="container flex h-16 items-center px-4 sm:px-8 max-w-7xl mx-auto">
                    <div className="mr-8 flex">
                        <Link to="/" className="mr-6 flex items-center space-x-2">
                            <span className="font-bold text-xl tracking-tight">Alpha<span className="text-[#0D9B97]">GBM</span></span>
                        </Link>
                        <nav className="flex items-center space-x-6 text-sm font-medium">
                            <Link to="/stock" className="transition-colors hover:text-[#0D9B97] text-slate-300">Analysis</Link>
                            <Link to="/options" className="transition-colors hover:text-[#0D9B97] text-slate-300">Options</Link>
                            <Link to="/pricing" className="transition-colors hover:text-[#0D9B97] text-slate-300">Pricing</Link>
                        </nav>
                    </div>

                    <div className="flex-1"></div>

                    <nav className="flex items-center gap-4">
                        <div className="flex items-center gap-2 mr-2 border-r border-white/10 pr-4">
                            <LanguageToggle />
                        </div>
                        {user ? (
                            <div className="flex items-center gap-4">
                                <Link to="/profile" className="text-sm font-medium hover:text-[#0D9B97] text-slate-300">Profile</Link>
                                <button
                                    onClick={handleLogout}
                                    className="text-sm font-medium hover:text-red-400 text-slate-300 transition-colors"
                                >
                                    Logout
                                </button>
                            </div>
                        ) : (
                            <Link to="/login" className="text-sm font-medium hover:text-[#0D9B97] text-slate-300">Login</Link>
                        )}
                    </nav>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 container py-8 px-4 sm:px-8 max-w-7xl mx-auto">
                <Outlet />
            </main>

            {/* Footer */}
            <footer className="py-8 border-t border-white/10 bg-[#09090B]">
                <div className="container flex flex-col items-center justify-center gap-4 text-center">
                    <p className="text-sm text-slate-500">
                        &copy; 2025 Alpha GBM. Data provided for educational purposes.
                    </p>
                </div>
            </footer>
        </div>
    );
}
