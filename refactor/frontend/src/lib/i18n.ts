
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Translations
const resources = {
    en: {
        translation: {
            "nav.stock": "Stock Analysis",
            "nav.options": "Options Research",
            "nav.pricing": "Pricing",
            "nav.profile": "Profile",
            "home.welcome": "Welcome to AlphaG",
            "home.desc": "Advanced AI-powered stock analysis and options research platform.",
            // Add more as needed
        }
    },
    zh: {
        translation: {
            "nav.stock": "股票分析",
            "nav.options": "期权研究",
            "nav.pricing": "定价方案",
            "nav.profile": "个人中心",
            "home.welcome": "欢迎来到 AlphaG",
            "home.desc": "先进的 AI 驱动股票分析与期权研究平台。",
        }
    }
};

i18n
    .use(initReactI18next)
    .init({
        resources,
        lng: "en",
        fallbackLng: "en",
        interpolation: {
            escapeValue: false
        }
    });

export default i18n;
