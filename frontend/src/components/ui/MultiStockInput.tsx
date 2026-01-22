/**
 * 多股票输入组件
 * 支持标签式输入 + 自动完成搜索
 * 最多支持 3 只股票
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { searchStocks } from '@/lib/stockData';
import type { StockInfo } from '@/lib/stockData';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';

interface MultiStockInputProps {
    values: string[];
    onChange: (values: string[]) => void;
    maxCount?: number;
    placeholder?: string;
    className?: string;
    disabled?: boolean;
}

export default function MultiStockInput({
    values,
    onChange,
    maxCount = 3,
    placeholder,
    className = '',
    disabled = false
}: MultiStockInputProps) {
    const { i18n } = useTranslation();
    const isZh = i18n.language.startsWith('zh');

    const [inputValue, setInputValue] = useState('');
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [suggestions, setSuggestions] = useState<StockInfo[]>([]);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const inputRef = useRef<HTMLInputElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const isMaxReached = values.length >= maxCount;

    // Update suggestions when input changes
    useEffect(() => {
        if (inputValue.trim().length > 0 && !isMaxReached) {
            // Filter out already selected stocks
            const results = searchStocks(inputValue, 8).filter(
                stock => !values.includes(stock.ticker)
            );
            setSuggestions(results);
            setSelectedIndex(-1);
        } else {
            setSuggestions([]);
        }
    }, [inputValue, values, isMaxReached]);

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
        setInputValue(newValue);
        setShowSuggestions(true);
    };

    const handleAddStock = useCallback((ticker: string) => {
        const normalizedTicker = ticker.trim().toUpperCase();
        if (!normalizedTicker) return;
        if (values.includes(normalizedTicker)) return;
        if (values.length >= maxCount) return;

        onChange([...values, normalizedTicker]);
        setInputValue('');
        setShowSuggestions(false);
        inputRef.current?.focus();
    }, [values, maxCount, onChange]);

    const handleSelectStock = (stock: StockInfo) => {
        handleAddStock(stock.ticker);
    };

    const handleRemoveStock = (ticker: string) => {
        onChange(values.filter(v => v !== ticker));
        inputRef.current?.focus();
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        // Handle backspace to remove last tag
        if (e.key === 'Backspace' && inputValue === '' && values.length > 0) {
            onChange(values.slice(0, -1));
            return;
        }

        // Handle Enter to add current input as ticker (if no suggestion selected)
        if (e.key === 'Enter') {
            e.preventDefault();
            if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
                handleSelectStock(suggestions[selectedIndex]);
            } else if (inputValue.trim()) {
                handleAddStock(inputValue);
            }
            return;
        }

        // Handle arrow navigation in suggestions
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
                return <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">A股</span>;
            default:
                return null;
        }
    };

    const defaultPlaceholder = isZh
        ? (isMaxReached ? '已达到最大数量' : `搜索添加股票（最多${maxCount}只）`)
        : (isMaxReached ? 'Maximum reached' : `Search to add stocks (max ${maxCount})`);

    return (
        <div ref={containerRef} className={`relative ${className}`}>
            {/* Input container with tags */}
            <div
                className={`
                    flex flex-wrap items-center gap-2
                    px-3 py-2 min-h-[42px]
                    bg-[#27272a] border border-white/20 rounded-md
                    focus-within:border-[#0D9B97] focus-within:ring-2 focus-within:ring-[#0D9B97]/20
                    transition-colors
                    ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                `}
                onClick={() => !disabled && inputRef.current?.focus()}
            >
                {/* Stock tags */}
                {values.map((ticker) => (
                    <div
                        key={ticker}
                        className="
                            flex items-center gap-1.5
                            px-2 py-1
                            bg-[#0D9B97]/20 border border-[#0D9B97]/30
                            rounded-md text-sm font-mono
                        "
                    >
                        <span className="text-[#0D9B97] font-semibold">{ticker}</span>
                        {!disabled && (
                            <button
                                type="button"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleRemoveStock(ticker);
                                }}
                                className="
                                    w-4 h-4 flex items-center justify-center
                                    rounded-full hover:bg-[#0D9B97]/30
                                    text-[#0D9B97] hover:text-white
                                    transition-colors
                                "
                                aria-label={`Remove ${ticker}`}
                            >
                                <X size={12} />
                            </button>
                        )}
                    </div>
                ))}

                {/* Input field */}
                {!isMaxReached && (
                    <input
                        ref={inputRef}
                        type="text"
                        value={inputValue}
                        onChange={handleInputChange}
                        onFocus={() => inputValue.trim().length > 0 && setShowSuggestions(true)}
                        onKeyDown={handleKeyDown}
                        placeholder={values.length === 0 ? (placeholder || defaultPlaceholder) : (isZh ? '继续添加...' : 'Add more...')}
                        disabled={disabled}
                        className="
                            flex-1 min-w-[120px]
                            bg-transparent border-none outline-none
                            text-white placeholder:text-slate-500
                        "
                        autoComplete="off"
                    />
                )}

                {/* Max reached indicator */}
                {isMaxReached && values.length > 0 && (
                    <span className="text-xs text-slate-500 ml-auto">
                        {isZh ? `已选 ${values.length}/${maxCount}` : `${values.length}/${maxCount} selected`}
                    </span>
                )}
            </div>

            {/* Suggestions dropdown */}
            {showSuggestions && suggestions.length > 0 && !isMaxReached && (
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

            {/* No results hint - allow direct input */}
            {showSuggestions && inputValue.trim().length > 0 && suggestions.length === 0 && !isMaxReached && (
                <div className="absolute z-50 w-full mt-1 bg-[#1c1c1e] border border-white/10 rounded-lg shadow-xl overflow-hidden">
                    <div
                        className="px-3 py-3 cursor-pointer hover:bg-white/5 transition-colors"
                        onClick={() => handleAddStock(inputValue)}
                    >
                        <div className="text-slate-400 text-sm">
                            {isZh
                                ? '未找到匹配的股票，点击直接添加：'
                                : 'No match found, click to add:'}
                        </div>
                        <div className="text-[#0D9B97] font-mono font-semibold mt-1">{inputValue}</div>
                    </div>
                </div>
            )}
        </div>
    );
}
