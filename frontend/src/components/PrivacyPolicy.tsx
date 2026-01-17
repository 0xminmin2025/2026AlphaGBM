import { useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function PrivacyPolicy() {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            {/* Privacy Policy Button */}
            <button
                onClick={() => setIsOpen(true)}
                className="text-xs sm:text-sm text-slate-400 hover:text-[#0D9B97] transition-colors underline underline-offset-2"
            >
                数据隐私声明
            </button>

            {/* Privacy Policy Modal */}
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <div className="relative w-full max-w-3xl max-h-[90vh] bg-[#18181B] border border-white/10 rounded-xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in duration-200">
                        {/* Header */}
                        <div className="flex items-center justify-between p-6 border-b border-white/10 bg-[#09090B]">
                            <h2 className="text-xl sm:text-2xl font-bold text-[#FAFAFA]">数据隐私声明</h2>
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
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">1. 信息收集</h3>
                                <p className="text-slate-300">
                                    我们收集以下类型的信息以提供和改进我们的服务：
                                </p>
                                <ul className="list-disc list-inside mt-2 space-y-1 ml-4 text-slate-400">
                                    <li>账户信息：当您注册账户时，我们收集您的电子邮件地址、用户名等信息</li>
                                    <li>使用数据：我们记录您如何使用我们的服务，包括访问时间、功能使用情况等</li>
                                    <li>财务数据：您提供的股票代码、期权数据等分析请求信息</li>
                                    <li>技术信息：设备信息、IP地址、浏览器类型等用于改善服务体验</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">2. 信息使用</h3>
                                <p className="text-slate-300">
                                    我们使用收集的信息用于以下目的：
                                </p>
                                <ul className="list-disc list-inside mt-2 space-y-1 ml-4 text-slate-400">
                                    <li>提供、维护和改进我们的金融服务和分析工具</li>
                                    <li>处理您的交易和订阅请求</li>
                                    <li>发送重要通知，如账户更新、服务变更等</li>
                                    <li>检测、预防和解决技术问题或欺诈行为</li>
                                    <li>提供客户支持并响应您的询问</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">3. 信息共享</h3>
                                <p className="text-slate-300">
                                    我们承诺保护您的隐私，不会向第三方出售您的个人信息。我们仅在以下情况下共享信息：
                                </p>
                                <ul className="list-disc list-inside mt-2 space-y-1 ml-4 text-slate-400">
                                    <li>服务提供商：与帮助我们运营服务的可信第三方（如支付处理、数据分析）</li>
                                    <li>法律要求：当法律、法规或政府机构要求时</li>
                                    <li>业务转让：在公司合并、收购或资产出售的情况下</li>
                                    <li>经您同意：在您明确授权的情况下</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">4. 数据安全</h3>
                                <p className="text-slate-300">
                                    我们采用行业标准的安全措施来保护您的个人信息：
                                </p>
                                <ul className="list-disc list-inside mt-2 space-y-1 ml-4 text-slate-400">
                                    <li>使用加密技术（SSL/TLS）保护数据传输</li>
                                    <li>实施访问控制和身份验证机制</li>
                                    <li>定期进行安全审计和漏洞评估</li>
                                    <li>对敏感数据进行加密存储</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">5. 您的权利</h3>
                                <p className="text-slate-300">
                                    根据适用的数据保护法律，您享有以下权利：
                                </p>
                                <ul className="list-disc list-inside mt-2 space-y-1 ml-4 text-slate-400">
                                    <li>访问权：查看我们持有的关于您的个人信息</li>
                                    <li>更正权：要求更正不准确或不完整的信息</li>
                                    <li>删除权：在符合法律要求的情况下删除您的个人信息</li>
                                    <li>限制处理权：限制我们对您个人信息的处理</li>
                                    <li>数据可携权：以结构化格式接收您的个人信息</li>
                                    <li>反对权：反对某些类型的个人信息处理</li>
                                </ul>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">6. Cookie 和跟踪技术</h3>
                                <p className="text-slate-300">
                                    我们使用 Cookie 和类似的跟踪技术来收集信息并改善您的体验。您可以通过浏览器设置管理 Cookie 偏好。但请注意，禁用某些 Cookie 可能影响服务功能。
                                </p>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">7. 数据保留</h3>
                                <p className="text-slate-300">
                                    我们仅在实现本声明所述目的所需的期限内保留您的个人信息。当不再需要时，我们会安全地删除或匿名化您的数据，除非法律要求我们保留更长时间。
                                </p>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">8. 儿童隐私</h3>
                                <p className="text-slate-300">
                                    我们的服务不面向18岁以下的未成年人。我们不会有意收集儿童的个人信息。如果您是父母或监护人，发现您的孩子向我们提供了个人信息，请联系我们。
                                </p>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">9. 国际数据传输</h3>
                                <p className="text-slate-300">
                                    您的信息可能被传输到并在您所在国家/地区以外进行处理。我们会采取适当措施确保您的信息受到与在原国家/地区同等水平的保护。
                                </p>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">10. 隐私政策更新</h3>
                                <p className="text-slate-300">
                                    我们可能会不时更新本隐私声明。重大变更时，我们会通过电子邮件或在网站上发布通知的方式告知您。我们建议您定期查看本页面以了解最新信息。更新后的隐私声明在发布后立即生效。
                                </p>
                            </div>

                            <div>
                                <h3 className="text-lg font-semibold text-[#FAFAFA] mb-3">11. 联系我们</h3>
                                <p className="text-slate-300">
                                    如果您对本隐私声明有任何问题、意见或疑虑，或希望行使您的数据保护权利，请通过以下方式联系我们：
                                </p>
                                <ul className="list-none mt-2 space-y-2 ml-4 text-slate-400">
                                    <li>• 电子邮件：通过网站右下角的反馈按钮</li>
                                    <li>• 地址：请通过反馈功能获取联系方式</li>
                                </ul>
                            </div>

                            <div className="pt-4 border-t border-white/10">
                                <p className="text-xs text-slate-500">
                                    最后更新时间：2026年1月
                                </p>
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="flex items-center justify-end gap-4 p-6 border-t border-white/10 bg-[#09090B]">
                            <Button
                                onClick={() => setIsOpen(false)}
                                className="bg-[#0D9B97] hover:bg-[#0a7a77] text-white px-6"
                            >
                                我已阅读并理解
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
