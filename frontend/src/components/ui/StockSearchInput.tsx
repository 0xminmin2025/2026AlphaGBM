import { useState, useRef, useEffect } from 'react';
import type { StockInfo } from '@/lib/stockData';
import { useTranslation } from 'react-i18next';
import { useStockSearch } from '@/hooks/useStockSearch';

interface StockSearchInputProps {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    className?: string;
    disabled?: boolean;
}

export default function StockSearchInput({
    value,
    onChange,
    placeholder,
    className = '',
    disabled = false
}: StockSearchInputProps) {
    const { i18n } = useTranslation();
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const inputRef = useRef<HTMLInputElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const { setQuery, results: suggestions, isSearching } = useStockSearch({ limit: 8 });

    // Sync value to search hook
    useEffect(() => {
        setQuery(value);
        setSelectedIndex(-1);
    }, [value, setQuery]);

    // Handle click outside to close suggestions
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setShowSuggestions(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newValue = e.target.value.toUpperCase();
        onChange(newValue);
        setShowSuggestions(true);
    };

    const handleSelectStock = (stock: StockInfo) => {
        onChange(stock.ticker);
        setShowSuggestions(false);
        inputRef.current?.blur();
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!showSuggestions || suggestions.length === 0) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setSelectedIndex(prev =>
                    prev < suggestions.length - 1 ? prev + 1 : 0
                );
                break;
            case 'ArrowUp':
                e.preventDefault();
                setSelectedIndex(prev =>
                    prev > 0 ? prev - 1 : suggestions.length - 1
                );
                break;
            case 'Enter':
                if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
                    e.preventDefault();
                    handleSelectStock(suggestions[selectedIndex]);
                }
                break;
            case 'Escape':
                setShowSuggestions(false);
                break;
        }
    };

    const getMarketBadge = (market: string) => {
        switch (market) {
            case 'US':
                return <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">US</span>;
            case 'HK':
                return <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400">HK</span>;
            case 'CN':
                return <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">A\u80a1</span>;
            default:
                return null;
        }
    };

    return (
        <div ref={containerRef} className="relative">
            <input
                ref={inputRef}
                type="text"
                value={value}
                onChange={handleInputChange}
                onFocus={() => value.trim().length > 0 && setShowSuggestions(true)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled}
                className={`w-full px-3 py-2 bg-[#27272a] border border-white/20 rounded-md text-white placeholder:text-slate-500 focus:border-[#0D9B97] focus:ring-2 focus:ring-[#0D9B97]/20 transition-colors ${className}`}
                autoComplete="off"
            />

            {/* Search hint */}
            {!showSuggestions && value.length === 0 && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500 pointer-events-none">
                    {i18n.language === 'zh' ? '\u652f\u6301\u4ee3\u7801/\u4e2d\u6587/\u62fc\u97f3' : 'Code/CN/Pinyin'}
                </div>
            )}

            {/* Suggestions dropdown */}
            {showSuggestions && suggestions.length > 0 && (
                <div className="absolute z-50 w-full mt-1 bg-[#1c1c1e] border border-white/10 rounded-lg shadow-xl overflow-hidden max-h-[320px] overflow-y-auto">
                    {suggestions.map((stock, index) => (
                        <div
                            key={stock.ticker}
                            className={`px-3 py-2.5 cursor-pointer transition-colors flex items-center justify-between gap-2 ${
                                index === selectedIndex
                                    ? 'bg-[#0D9B97]/20 border-l-2 border-[#0D9B97]'
                                    : 'hover:bg-white/5 border-l-2 border-transparent'
                            }`}
                            onClick={() => handleSelectStock(stock)}
                            onMouseEnter={() => setSelectedIndex(index)}
                        >
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <span className="font-mono font-semibold text-[#0D9B97]">
                                        {stock.ticker}
                                    </span>
                                    {getMarketBadge(stock.market)}
                                </div>
                                <div className="text-sm text-slate-400 truncate">
                                    {stock.nameCn}
                                    {stock.nameEn && (
                                        <span className="text-slate-500 ml-1">
                                            ({stock.nameEn})
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div className="text-xs text-slate-600 font-mono">
                                {stock.pinyin}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* No results hint */}
            {showSuggestions && value.trim().length > 0 && suggestions.length === 0 && (
                <div className="absolute z-50 w-full mt-1 bg-[#1c1c1e] border border-white/10 rounded-lg shadow-xl p-4 text-center">
                    {isSearching ? (
                        <div className="text-slate-400 text-sm">
                            {i18n.language === 'zh' ? '\u641c\u7d22\u4e2d...' : 'Searching...'}
                        </div>
                    ) : (
                        <>
                            <div className="text-slate-400 text-sm">
                                {i18n.language === 'zh'
                                    ? '\u672a\u627e\u5230\u5339\u914d\u7684\u80a1\u7968\uff0c\u5c06\u76f4\u63a5\u4f7f\u7528\u4ee3\u7801'
                                    : 'No match found, will use ticker directly'}
                            </div>
                            <div className="text-[#0D9B97] font-mono mt-1">{value}</div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
