import { Loader2 } from 'lucide-react';

interface LoadingScreenProps {
    message?: string;
}

export default function LoadingScreen({ message = "加载中..." }: LoadingScreenProps) {
    return (
        <div className="fixed inset-0 bg-[#09090B] flex items-center justify-center z-50">
            <div className="flex flex-col items-center space-y-4">
                {/* Logo/Brand */}
                <div className="flex items-center space-x-2 mb-4">
                    <span className="font-bold text-2xl tracking-tight text-[#FAFAFA]">
                        Alpha<span className="text-[#0D9B97]">GBM</span>
                    </span>
                </div>

                {/* Spinner */}
                <div className="relative">
                    <Loader2 className="w-12 h-12 animate-spin text-[#0D9B97]" />
                    <div className="absolute inset-0 rounded-full border-2 border-[#0D9B97]/20"></div>
                </div>

                {/* Loading Message */}
                <p className="text-slate-400 text-sm font-medium">{message}</p>

                {/* Loading Dots Animation */}
                <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-[#0D9B97] rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                    <div className="w-2 h-2 bg-[#0D9B97] rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                    <div className="w-2 h-2 bg-[#0D9B97] rounded-full animate-bounce"></div>
                </div>
            </div>

            {/* Background Pattern (Optional) */}
            <div className="absolute inset-0 opacity-5">
                <div
                    className="w-full h-full"
                    style={{
                        backgroundImage: `radial-gradient(circle at 25% 25%, #0D9B97 1px, transparent 1px)`,
                        backgroundSize: '24px 24px'
                    }}
                />
            </div>
        </div>
    );
}