import { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/components/auth/AuthProvider';
import { useUserData } from '@/components/auth/UserDataProvider';
import LoadingScreen from '../ui/LoadingScreen';
import FeedbackButton from '../FeedbackButton';
import PrivacyPolicy from '../PrivacyPolicy';
import { useTranslation } from 'react-i18next';
import { Menu, X } from 'lucide-react';
import i18n from '@/lib/i18n';

export default function MainLayout() {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const { user, signOut } = useAuth();
    const { isInitialLoading } = useUserData();
    const navigate = useNavigate();
    const location = useLocation();
    const { t } = useTranslation();

    // 处理股票分析导航 - 无论当前在哪个页面，点击都重置为新分析
    const handleStockNavigation = (e: React.MouseEvent) => {
        e.preventDefault();
        // 如果已经在 /stock 页面，使用 replace 强制刷新
        if (location.pathname === '/stock') {
            // 先导航到临时路径再导航回来，触发 location.key 变化
            navigate('/stock', { replace: true, state: { reset: Date.now() } });
        } else {
            navigate('/stock');
        }
        setIsMobileMenuOpen(false);
    };

    // 处理期权研究导航 - 无论当前在哪个页面，点击都重置为新分析
    const handleOptionsNavigation = (e: React.MouseEvent) => {
        e.preventDefault();
        // 如果已经在 /options 页面，使用 replace 强制刷新
        if (location.pathname === '/options') {
            navigate('/options', { replace: true, state: { reset: Date.now() } });
        } else {
            navigate('/options');
        }
        setIsMobileMenuOpen(false);
    };

    const handleLogout = async () => {
        await signOut();
        navigate('/login');
        setIsMobileMenuOpen(false); // Close mobile menu after logout
    };

    const closeMobileMenu = () => {
        setIsMobileMenuOpen(false);
    };

    const toggleLang = () => {
        i18n.changeLanguage(i18n.language === 'zh' ? 'en' : 'zh');
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
                        <img src="/logo.png" alt="AlphaGBM" className="h-8 w-8" />
                        <span className="font-bold text-xl tracking-tight">Alpha<span className="text-[#0D9B97]">GBM</span></span>
                    </Link>

                    {/* Desktop Navigation */}
                    <div className="hidden md:flex items-center space-x-8">
                        <nav className="flex items-center space-x-6 text-sm font-medium">
                            <a href="/options" onClick={handleOptionsNavigation} className="transition-colors hover:text-[#0D9B97] text-slate-300 cursor-pointer">{t('nav.options')}</a>
                            <Link to="/options/reverse" className="transition-colors hover:text-[#0D9B97] text-slate-300">{t('nav.reverseScore')}</Link>
                            <a href="/stock" onClick={handleStockNavigation} className="transition-colors hover:text-[#0D9B97] text-slate-300 cursor-pointer">{t('nav.stock')}</a>
                            <Link to="/pricing" className="transition-colors hover:text-[#0D9B97] text-slate-300">{t('nav.pricing')}</Link>
                        </nav>

                        <div className="flex items-center gap-4">
                            <button onClick={toggleLang} className="text-sm font-mono border border-slate-700 px-3 py-1 rounded hover:bg-slate-800 transition-colors">
                                {i18n.language === 'zh' ? 'EN' : '中'}
                            </button>
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
                            <a
                                href="/options"
                                className="text-sm font-medium hover:text-[#0D9B97] text-slate-300 py-2 transition-colors cursor-pointer"
                                onClick={handleOptionsNavigation}
                            >
                                {t('nav.options')}
                            </a>
                            <Link
                                to="/options/reverse"
                                className="text-sm font-medium hover:text-[#0D9B97] text-slate-300 py-2 transition-colors"
                                onClick={closeMobileMenu}
                            >
                                {t('nav.reverseScore')}
                            </Link>
                            <a
                                href="/stock"
                                className="text-sm font-medium hover:text-[#0D9B97] text-slate-300 py-2 transition-colors cursor-pointer"
                                onClick={handleStockNavigation}
                            >
                                {t('nav.stock')}
                            </a>
                            <Link
                                to="/pricing"
                                className="text-sm font-medium hover:text-[#0D9B97] text-slate-300 py-2 transition-colors"
                                onClick={closeMobileMenu}
                            >
                                {t('nav.pricing')}
                            </Link>

                            <div className="border-t border-white/10 pt-4 mt-4 space-y-4">
                                <button onClick={toggleLang} className="text-sm font-mono border border-slate-700 px-3 py-1 rounded hover:bg-slate-800 transition-colors">
                                    {i18n.language === 'zh' ? 'EN' : '中'}
                                </button>
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
                    <div className="flex items-center gap-6 flex-wrap justify-center">
                        <p className="text-xs sm:text-sm text-slate-500">
                            {t('footer.copyright')}
                        </p>
                        <span className="text-slate-600">|</span>
                        <PrivacyPolicy />
                    </div>
                </div>
            </footer>

            {/* Feedback Button */}
            <FeedbackButton />
        </div>
    );
}
