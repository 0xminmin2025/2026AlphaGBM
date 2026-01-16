import { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/components/auth/AuthProvider';
import { useUserData } from '@/components/auth/UserDataProvider';
import { LanguageToggle } from '../ui/language-toggle';
import LoadingScreen from '../ui/LoadingScreen';
import { useTranslation } from 'react-i18next';
import { Menu, X } from 'lucide-react';

export default function MainLayout() {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const { user, signOut } = useAuth();
    const { isInitialLoading } = useUserData();
    const navigate = useNavigate();
    const { t } = useTranslation();

    const handleLogout = async () => {
        await signOut();
        navigate('/login');
        setIsMobileMenuOpen(false); // Close mobile menu after logout
    };

    const closeMobileMenu = () => {
        setIsMobileMenuOpen(false);
    };

    // Show loading screen when user data is being initially loaded
    // Add timeout to prevent infinite loading
    useEffect(() => {
        if (isInitialLoading && user) {
            const timeout = setTimeout(() => {
                console.warn("UserData loading timeout in MainLayout");
            }, 10000); // 10 second warning
            return () => clearTimeout(timeout);
        }
    }, [isInitialLoading, user]);

    if (isInitialLoading && user) {
        return <LoadingScreen message={t('common.loading')} />;
    }

    return (
        <div className="min-h-screen bg-[#09090B] text-[#FAFAFA] flex flex-col font-sans">
            {/* Mobile-Responsive Navbar */}
            <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-[#09090B]/80 backdrop-blur-md">
                <div className="container flex h-16 items-center justify-between px-4 sm:px-8 max-w-7xl mx-auto">
                    {/* Logo */}
                    <Link to="/" className="flex items-center space-x-2">
                        <span className="font-bold text-xl tracking-tight">Alpha<span className="text-[#0D9B97]">GBM</span></span>
                    </Link>

                    {/* Desktop Navigation */}
                    <div className="hidden md:flex items-center space-x-8">
                        <nav className="flex items-center space-x-6 text-sm font-medium">
                            <Link to="/stock" className="transition-colors hover:text-[#0D9B97] text-slate-300">{t('nav.stock')}</Link>
                            <Link to="/options" className="transition-colors hover:text-[#0D9B97] text-slate-300">{t('nav.options')}</Link>
                            <Link to="/pricing" className="transition-colors hover:text-[#0D9B97] text-slate-300">{t('nav.pricing')}</Link>
                        </nav>

                        <div className="flex items-center gap-4">
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
                        </div>
                    </div>

                    {/* Mobile Menu Button */}
                    <button
                        className="md:hidden p-2 text-slate-300 hover:text-[#0D9B97] transition-colors"
                        onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                        aria-label="Toggle mobile menu"
                    >
                        {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                    </button>
                </div>

                {/* Mobile Navigation Menu */}
                {isMobileMenuOpen && (
                    <div className="md:hidden bg-[#09090B]/95 backdrop-blur-md border-t border-white/10">
                        <nav className="flex flex-col px-4 py-4 space-y-4">
                            <Link
                                to="/stock"
                                className="text-sm font-medium hover:text-[#0D9B97] text-slate-300 py-2 transition-colors"
                                onClick={closeMobileMenu}
                            >
                                {t('nav.stock')}
                            </Link>
                            <Link
                                to="/options"
                                className="text-sm font-medium hover:text-[#0D9B97] text-slate-300 py-2 transition-colors"
                                onClick={closeMobileMenu}
                            >
                                {t('nav.options')}
                            </Link>
                            <Link
                                to="/pricing"
                                className="text-sm font-medium hover:text-[#0D9B97] text-slate-300 py-2 transition-colors"
                                onClick={closeMobileMenu}
                            >
                                {t('nav.pricing')}
                            </Link>

                            <div className="border-t border-white/10 pt-4 mt-4 space-y-4">
                                <div className="flex items-center gap-2">
                                    <LanguageToggle />
                                </div>
                                {user ? (
                                    <div className="space-y-4">
                                        <Link
                                            to="/profile"
                                            className="text-sm font-medium hover:text-[#0D9B97] text-slate-300 py-2 transition-colors block"
                                            onClick={closeMobileMenu}
                                        >
                                            {t('nav.profile')}
                                        </Link>
                                        <button
                                            onClick={handleLogout}
                                            className="text-sm font-medium hover:text-red-400 text-slate-300 transition-colors text-left py-2"
                                        >
                                            {t('nav.logout')}
                                        </button>
                                    </div>
                                ) : (
                                    <Link
                                        to="/login"
                                        className="text-sm font-medium hover:text-[#0D9B97] text-slate-300 py-2 transition-colors block"
                                        onClick={closeMobileMenu}
                                    >
                                        {t('nav.login')}
                                    </Link>
                                )}
                            </div>
                        </nav>
                    </div>
                )}
            </header>

            {/* Main Content */}
            <main className="flex-1 container py-4 px-4 sm:py-8 sm:px-8 max-w-7xl mx-auto">
                <Outlet />
            </main>

            {/* Footer */}
            <footer className="py-6 sm:py-8 border-t border-white/10 bg-[#09090B]">
                <div className="container flex flex-col items-center justify-center gap-4 text-center px-4 sm:px-8 max-w-7xl mx-auto">
                    <p className="text-xs sm:text-sm text-slate-500">
                        {t('footer.copyright')}
                    </p>
                </div>
            </footer>
        </div>
    );
}
