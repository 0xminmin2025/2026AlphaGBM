import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface SelectOption {
    value: string;
    label: string;
    description?: string;
}

interface CustomSelectProps {
    options: SelectOption[];
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    className?: string;
}

export default function CustomSelect({ options, value, onChange, placeholder, className = '' }: CustomSelectProps) {
    const [isOpen, setIsOpen] = useState(false);

    const selectedOption = options.find(option => option.value === value);

    const handleSelect = (optionValue: string) => {
        onChange(optionValue);
        setIsOpen(false);
    };

    return (
        <div className={`relative ${className}`}>
            {/* Selected value display */}
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="w-full bg-[#27272a] border border-white/20 text-[#fafafa] px-4 py-3 rounded-lg text-left flex items-center justify-between transition-all duration-200 hover:border-[#0D9B97]/50 focus:border-[#0D9B97] focus:outline-none focus:ring-2 focus:ring-[#0D9B97]/20"
            >
                <span className="flex-1">
                    {selectedOption ? selectedOption.label : placeholder || 'Select an option...'}
                </span>
                {isOpen ? (
                    <ChevronUp className="w-4 h-4 text-slate-400 ml-2" />
                ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400 ml-2" />
                )}
            </button>

            {/* Dropdown menu */}
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 z-10"
                        onClick={() => setIsOpen(false)}
                    />

                    {/* Options */}
                    <div className="absolute top-full left-0 right-0 mt-1 bg-[#1c1c1e] border border-white/20 rounded-lg shadow-2xl z-20 overflow-hidden">
                        {options.map((option) => (
                            <button
                                key={option.value}
                                type="button"
                                onClick={() => handleSelect(option.value)}
                                className={`w-full px-4 py-3 text-left transition-all duration-150 border-b border-white/10 last:border-b-0 hover:bg-[#0D9B97]/20 hover:border-l-4 hover:border-l-[#0D9B97] ${
                                    option.value === value
                                        ? 'bg-[#0D9B97]/10 border-l-4 border-l-[#0D9B97] text-[#0D9B97]'
                                        : 'text-[#fafafa]'
                                }`}
                            >
                                <div className="font-medium text-sm">
                                    {option.label}
                                </div>
                                {option.description && (
                                    <div className="text-xs text-slate-400 mt-1 leading-relaxed">
                                        {option.description}
                                    </div>
                                )}
                            </button>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}