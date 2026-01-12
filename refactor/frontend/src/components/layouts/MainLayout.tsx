import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/components/auth/AuthProvider';
import { useUserData } from '@/components/auth/UserDataProvider';
import { LanguageToggle } from '../ui/language-toggle';
import LoadingScreen from '../ui/LoadingScreen';
import { useTranslation } from 'react-i18next';

export default function MainLayout() {
    const { user, signOut } = useAuth();
    const { isInitialLoading } = useUserData();
    const navigate = useNavigate();
    const { t } = useTranslation();

    const handleLogout = async () => {
        await signOut();
        navigate('/login');
    };

    // Show loading screen when user data is being initially loaded
    if (isInitialLoading && user) {
        return <LoadingScreen message={t('common.loading')} />;
    }

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
                            <Link to="/stock" className="transition-colors hover:text-[#0D9B97] text-slate-300">{t('nav.stock')}</Link>
                            <Link to="/options" className="transition-colors hover:text-[#0D9B97] text-slate-300">{t('nav.options')}</Link>
                            <Link to="/pricing" className="transition-colors hover:text-[#0D9B97] text-slate-300">{t('nav.pricing')}</Link>
                        </nav>
                    </div>

                    <div className="flex-1"></div>

                    <nav className="flex items-center gap-4">
                        <div className="flex items-center gap-2 mr-2 border-r border-white/10 pr-4">
                            <LanguageToggle />
                        </div>
                        {user ? (
                            <div className="flex items-center gap-4">
                                <Link to="/profile" className="text-sm font-medium hover:text-[#0D9B97] text-slate-300">{t('nav.profile')}</Link>
                                <button
                                    onClick={handleLogout}
                                    className="text-sm font-medium hover:text-red-400 text-slate-300 transition-colors"
                                >
                                    {t('nav.logout')}
                                </button>
                            </div>
                        ) : (
                            <Link to="/login" className="text-sm font-medium hover:text-[#0D9B97] text-slate-300">{t('nav.login')}</Link>
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
                        {t('footer.copyright')}
                    </p>
                </div>
            </footer>
        </div>
    );
}
