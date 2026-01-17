import { useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTranslation } from 'react-i18next';

export default function PrivacyPolicy() {
    const [isOpen, setIsOpen] = useState(false);
    const { t } = useTranslation();

    return (
        <>
            {/* Privacy Policy Button */}
            <button
                onClick={() => setIsOpen(true)}
                className="text-xs sm:text-sm text-slate-400 hover:text-[#0D9B97] transition-colors underline underline-offset-2"
            >
                {t('privacy.button')}
            </button>

            {/* Privacy Policy Modal */}
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <div className="relative w-full max-w-3xl max-h-[90vh] bg-[#18181B] border border-white/10 rounded-xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
                        {/* Header */}
                        <div className="flex items-center justify-between p-6 border-b border-white/10 bg-[#09090B]">
                            <h2 className="text-xl sm:text-2xl font-bold text-[#FAFAFA]">{t('privacy.title')}</h2>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => setIsOpen(false)}
                                className="text-slate-400 hover:text-[#FAFAFA] hover:bg-white/5 rounded-lg"
                            >
                                <X className="w-5 h-5" />
                            </Button>
                        </div>

                        {/* Content */}
                        <div className="flex-1 overflow-y-auto p-6 sm:p-8 text-sm sm:text-base text-slate-300 leading-relaxed space-y-6">
                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section1.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section1.desc')}
                                </p>
                                <ul className="list-disc list-inside mt-2 space-y-1 ml-4 text-slate-400">
                                    <li>{t('privacy.section1.item1')}</li>
                                    <li>{t('privacy.section1.item2')}</li>
                                    <li>{t('privacy.section1.item3')}</li>
                                    <li>{t('privacy.section1.item4')}</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section2.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section2.desc')}
                                </p>
                                <ul className="list-disc list-inside mt-2 space-y-1 ml-4 text-slate-400">
                                    <li>{t('privacy.section2.item1')}</li>
                                    <li>{t('privacy.section2.item2')}</li>
                                    <li>{t('privacy.section2.item3')}</li>
                                    <li>{t('privacy.section2.item4')}</li>
                                    <li>{t('privacy.section2.item5')}</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section3.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section3.desc')}
                                </p>
                                <ul className="list-disc list-inside mt-2 space-y-1 ml-4 text-slate-400">
                                    <li>{t('privacy.section3.item1')}</li>
                                    <li>{t('privacy.section3.item2')}</li>
                                    <li>{t('privacy.section3.item3')}</li>
                                    <li>{t('privacy.section3.item4')}</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section4.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section4.desc')}
                                </p>
                                <ul className="list-disc list-inside mt-2 space-y-1 ml-4 text-slate-400">
                                    <li>{t('privacy.section4.item1')}</li>
                                    <li>{t('privacy.section4.item2')}</li>
                                    <li>{t('privacy.section4.item3')}</li>
                                    <li>{t('privacy.section4.item4')}</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section5.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section5.desc')}
                                </p>
                                <ul className="list-disc list-inside mt-2 space-y-1 ml-4 text-slate-400">
                                    <li>{t('privacy.section5.item1')}</li>
                                    <li>{t('privacy.section5.item2')}</li>
                                    <li>{t('privacy.section5.item3')}</li>
                                    <li>{t('privacy.section5.item4')}</li>
                                    <li>{t('privacy.section5.item5')}</li>
                                    <li>{t('privacy.section5.item6')}</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section6.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section6.desc')}
                                </p>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section7.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section7.desc')}
                                </p>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section8.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section8.desc')}
                                </p>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section9.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section9.desc')}
                                </p>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section10.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section10.desc')}
                                </p>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">{t('privacy.section11.title')}</h3>
                                <p className="text-slate-300">
                                    {t('privacy.section11.desc')}
                                </p>
                                <ul className="list-none mt-2 space-y-2 ml-4 text-slate-400">
                                    <li>• {t('privacy.section11.item1')}</li>
                                    <li>• {t('privacy.section11.item2')}</li>
                                </ul>
                            </div>

                            <div className="pt-4 border-t border-white/10">
                                <p className="text-xs text-slate-500">
                                    {t('privacy.lastUpdated')}
                                </p>
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="flex items-center justify-end gap-4 p-6 border-t border-white/10 bg-[#09090B]">
                            <Button
                                onClick={() => setIsOpen(false)}
                                className="bg-[#0D9B97] hover:bg-[#0a7a77] text-white px-6"
                            >
                                {t('privacy.readAndUnderstood')}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
