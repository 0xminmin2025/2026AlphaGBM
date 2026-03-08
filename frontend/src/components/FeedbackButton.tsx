import { useState } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { MessageSquare, X, Send } from 'lucide-react';
import { useToastHelpers } from '@/components/ui/toast';

export default function FeedbackButton() {
    const [isOpen, setIsOpen] = useState(false);
    const [feedback, setFeedback] = useState('');
    const [feedbackType, setFeedbackType] = useState('bug'); // bug, suggestion, question
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const { user } = useAuth();
    const toast = useToastHelpers();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!feedback.trim()) return;

        setSubmitting(true);
        try {
            await api.post('/feedback', {
                type: feedbackType,
                content: feedback.trim(),
                ticker: null // Can be extended to include current ticker if on analysis page
            });

            setSubmitted(true);
            setTimeout(() => {
                setSubmitted(false);
                setFeedback('');
                setIsOpen(false);
            }, 2000);
        } catch (error: any) {
            console.error('Failed to submit feedback:', error);
            toast.error('提交失败', '请稍后重试');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <>
            {/* Floating Button */}
            <button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-[#0D9B97] hover:bg-[#0a7a77] text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center group"
                aria-label="反馈"
            >
                <MessageSquare size={24} className="group-hover:scale-110 transition-transform" />
            </button>

            {/* Feedback Modal */}
            {isOpen && (
                <div 
                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
                    onClick={() => !submitting && setIsOpen(false)}
                >
                    <div 
                        className="bg-[#18181B] border border-white/10 rounded-xl shadow-2xl w-full max-w-md p-6 relative"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Close Button */}
                        <button
                            onClick={() => setIsOpen(false)}
                            disabled={submitting}
                            className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors disabled:opacity-50"
                            aria-label="关闭"
                        >
                            <X size={20} />
                        </button>

                        {/* Header */}
                        <div className="mb-6">
                            <h3 className="text-xl font-bold text-white mb-2">用户反馈</h3>
                            <p className="text-sm text-slate-400">
                                {user ? `欢迎，${user.email}` : '您的反馈对我们很重要'}
                            </p>
                        </div>

                        {submitted ? (
                            <div className="text-center py-8">
                                <div className="w-16 h-16 bg-[#0D9B97]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <Send size={32} className="text-[#0D9B97]" />
                                </div>
                                <p className="text-white font-medium">感谢您的反馈！</p>
                                <p className="text-slate-400 text-sm mt-2">我们会认真处理您的建议</p>
                            </div>
                        ) : (
                            <form onSubmit={handleSubmit} className="space-y-4">
                                {/* Feedback Type */}
                                <div>
                                    <label className="block text-sm font-medium text-slate-300 mb-2">
                                        反馈类型
                                    </label>
                                    <div className="grid grid-cols-3 gap-2">
                                        {[
                                            { value: 'bug', label: '问题' },
                                            { value: 'suggestion', label: '建议' },
                                            { value: 'question', label: '咨询' }
                                        ].map((type) => (
                                            <button
                                                key={type.value}
                                                type="button"
                                                onClick={() => setFeedbackType(type.value)}
                                                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                                                    feedbackType === type.value
                                                        ? 'bg-[#0D9B97] text-white'
                                                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                                                }`}
                                            >
                                                {type.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Feedback Content */}
                                <div>
                                    <label htmlFor="feedback-content" className="block text-sm font-medium text-slate-300 mb-2">
                                        详细描述
                                    </label>
                                    <textarea
                                        id="feedback-content"
                                        value={feedback}
                                        onChange={(e) => setFeedback(e.target.value)}
                                        placeholder="请描述您遇到的问题、建议或疑问..."
                                        rows={6}
                                        className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#0D9B97] focus:border-transparent resize-none"
                                        required
                                        disabled={submitting}
                                    />
                                </div>

                                {/* Submit Button */}
                                <button
                                    type="submit"
                                    disabled={!feedback.trim() || submitting}
                                    className="w-full py-3 bg-[#0D9B97] hover:bg-[#0a7a77] text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                    {submitting ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                            <span>提交中...</span>
                                        </>
                                    ) : (
                                        <>
                                            <Send size={18} />
                                            <span>提交反馈</span>
                                        </>
                                    )}
                                </button>
                            </form>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
