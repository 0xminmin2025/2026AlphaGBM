import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import StockSearchInput from '@/components/ui/StockSearchInput';
import { useTranslation } from 'react-i18next';
import { Upload, Camera, FileText, X, Loader2 } from 'lucide-react';

// Score result type
interface ScoreResult {
    score: number;
    breakdown: {
        premium_income?: number;
        trend_match?: number;
        resistance_strength?: number;
        support_strength?: number;
        atr_safety?: number;
        liquidity?: number;
        time_value?: number;
        volatility?: number;
        risk_reward?: number;
        [key: string]: number | undefined;
    };
    style_label: string;
    risk_level: string;
    risk_color: string;
    trend_warning: string | null;
    win_probability?: number;
    max_profit_pct?: number;
    max_loss_pct?: number;
}

interface ReverseScoreResponse {
    success: boolean;
    symbol: string;
    option_type: string;
    strike: number;
    expiry_date: string;
    current_price: number;
    scores: {
        sell_call?: ScoreResult;
        buy_call?: ScoreResult;
        sell_put?: ScoreResult;
        buy_put?: ScoreResult;
    };
    trend_info?: {
        trend: string;
        trend_strength: number;
        support_levels: number[];
        resistance_levels: number[];
    };
    error?: string;
}

// CSS styles
const styles = `
    .reverse-score-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 1.5rem;
    }

    .header-section {
        background-color: hsl(240, 6%, 10%);
        border: 1px solid hsl(240, 3.7%, 15.9%);
        border-radius: 0.75rem;
        padding: 1.5rem 2rem;
        text-align: center;
        margin-bottom: 1.5rem;
    }

    .form-card {
        background-color: hsl(240, 6%, 10%);
        border: 1px solid hsl(240, 3.7%, 15.9%);
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .form-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
    }

    @media (max-width: 640px) {
        .form-grid {
            grid-template-columns: 1fr;
        }
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .form-group.full-width {
        grid-column: span 2;
    }

    @media (max-width: 640px) {
        .form-group.full-width {
            grid-column: span 1;
        }
    }

    .form-label {
        font-size: 0.875rem;
        font-weight: 500;
        color: hsl(240, 5%, 64.9%);
    }

    .form-input {
        background-color: hsl(240, 5%, 6%);
        border: 1px solid hsl(240, 3.7%, 15.9%);
        border-radius: 0.5rem;
        padding: 0.75rem 1rem;
        color: white;
        font-size: 1rem;
        transition: border-color 0.2s;
    }

    .form-input:focus {
        outline: none;
        border-color: hsl(178, 78%, 32%);
    }

    .form-input::placeholder {
        color: hsl(240, 5%, 40%);
    }

    .option-type-toggle {
        display: flex;
        gap: 0.5rem;
    }

    .option-type-btn {
        flex: 1;
        padding: 0.75rem;
        border-radius: 0.5rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        border: 1px solid hsl(240, 3.7%, 15.9%);
        background-color: hsl(240, 5%, 6%);
        color: hsl(240, 5%, 64.9%);
    }

    .option-type-btn.call.active {
        background-color: hsl(142, 76%, 36%);
        border-color: hsl(142, 76%, 36%);
        color: white;
    }

    .option-type-btn.put.active {
        background-color: hsl(0, 84%, 60%);
        border-color: hsl(0, 84%, 60%);
        color: white;
    }

    .result-card {
        background-color: hsl(240, 6%, 10%);
        border: 1px solid hsl(240, 3.7%, 15.9%);
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid hsl(240, 3.7%, 15.9%);
    }

    .strategy-name {
        font-size: 1.125rem;
        font-weight: 600;
    }

    .score-badge {
        font-size: 1.5rem;
        font-weight: bold;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
    }

    .score-high {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10B981;
    }

    .score-medium {
        background-color: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
    }

    .score-low {
        background-color: rgba(239, 68, 68, 0.2);
        color: #EF4444;
    }

    .style-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-top: 0.5rem;
    }

    .breakdown-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.75rem;
        margin-top: 1rem;
    }

    @media (max-width: 640px) {
        .breakdown-grid {
            grid-template-columns: 1fr;
        }
    }

    .breakdown-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0.75rem;
        background-color: hsl(240, 5%, 8%);
        border-radius: 0.375rem;
    }

    .breakdown-label {
        font-size: 0.875rem;
        color: hsl(240, 5%, 64.9%);
    }

    .breakdown-score {
        font-weight: 500;
    }

    .trend-warning {
        margin-top: 1rem;
        padding: 0.75rem 1rem;
        background-color: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 0.5rem;
        color: #F59E0B;
        font-size: 0.875rem;
    }

    .stock-info {
        display: flex;
        gap: 2rem;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid hsl(240, 3.7%, 15.9%);
    }

    .stock-info-item {
        text-align: center;
    }

    .stock-info-label {
        font-size: 0.75rem;
        color: hsl(240, 5%, 64.9%);
    }

    .stock-info-value {
        font-size: 1.125rem;
        font-weight: 600;
        color: white;
    }

    .error-message {
        background-color: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 0.5rem;
        padding: 1rem;
        color: #EF4444;
        text-align: center;
    }

    .loading-overlay {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 3rem;
        color: hsl(240, 5%, 64.9%);
    }

    .spinner {
        width: 40px;
        height: 40px;
        border: 3px solid hsl(240, 3.7%, 15.9%);
        border-top-color: hsl(178, 78%, 32%);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 1rem;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    /* Input Mode Tabs */
    .input-mode-tabs {
        display: flex;
        gap: 0;
        margin-bottom: 1.5rem;
        border-radius: 0.5rem;
        overflow: hidden;
        border: 1px solid hsl(240, 3.7%, 15.9%);
    }

    .input-mode-tab {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.875rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        background-color: hsl(240, 5%, 6%);
        color: hsl(240, 5%, 64.9%);
        border: none;
    }

    .input-mode-tab:first-child {
        border-right: 1px solid hsl(240, 3.7%, 15.9%);
    }

    .input-mode-tab.active {
        background-color: hsl(178, 78%, 32%);
        color: white;
    }

    .input-mode-tab:hover:not(.active) {
        background-color: hsl(240, 5%, 10%);
    }

    /* Image Upload Area - Compact version */
    .image-upload-area {
        border: 1px dashed hsl(240, 3.7%, 25%);
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
        background-color: hsl(240, 5%, 6%);
    }

    .image-upload-area:hover {
        border-color: hsl(178, 78%, 32%);
        background-color: hsl(240, 5%, 8%);
    }

    .image-upload-area.dragging {
        border-color: hsl(178, 78%, 42%);
        background-color: hsl(178, 78%, 10%);
    }

    .image-upload-area.has-image {
        border-style: solid;
        border-color: hsl(178, 78%, 32%);
    }

    .upload-icon {
        width: 28px;
        height: 28px;
        margin: 0 auto 0.5rem;
        color: hsl(240, 5%, 50%);
    }

    .upload-text {
        font-size: 0.8rem;
        color: hsl(240, 5%, 64.9%);
        margin-bottom: 0.25rem;
    }

    .upload-hint {
        font-size: 0.7rem;
        color: hsl(240, 5%, 50%);
    }

    /* Secondary tab style for upload */
    .input-mode-tab.secondary {
        font-size: 0.8rem;
        padding: 0.625rem 0.75rem;
    }

    .input-mode-tab.secondary svg {
        width: 14px;
        height: 14px;
    }

    /* Image Preview */
    .image-preview-container {
        position: relative;
        display: inline-block;
        max-width: 100%;
    }

    .image-preview {
        max-width: 100%;
        max-height: 300px;
        border-radius: 0.5rem;
        object-fit: contain;
    }

    .image-remove-btn {
        position: absolute;
        top: -8px;
        right: -8px;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background-color: hsl(0, 84%, 60%);
        color: white;
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
    }

    .image-remove-btn:hover {
        background-color: hsl(0, 84%, 50%);
        transform: scale(1.1);
    }

    /* Recognition Result */
    .recognition-result {
        margin-top: 1rem;
        padding: 1rem;
        background-color: hsl(142, 76%, 10%);
        border: 1px solid hsl(142, 76%, 36%);
        border-radius: 0.5rem;
    }

    .recognition-result.error {
        background-color: hsl(0, 84%, 10%);
        border-color: hsl(0, 84%, 50%);
    }

    .recognition-result-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
        font-weight: 500;
        color: hsl(142, 76%, 50%);
    }

    .recognition-result.error .recognition-result-header {
        color: hsl(0, 84%, 60%);
    }

    .recognition-fields {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.5rem;
        font-size: 0.875rem;
    }

    @media (max-width: 640px) {
        .recognition-fields {
            grid-template-columns: 1fr;
        }
    }

    .recognition-field {
        display: flex;
        justify-content: space-between;
        padding: 0.375rem 0.5rem;
        background-color: hsl(240, 5%, 6%);
        border-radius: 0.25rem;
    }

    .recognition-field-label {
        color: hsl(240, 5%, 64.9%);
    }

    .recognition-field-value {
        font-weight: 500;
        color: white;
    }

    .recognition-actions {
        display: flex;
        gap: 0.75rem;
        margin-top: 1rem;
    }
`;

// Breakdown label translations
const breakdownLabels: Record<string, { en: string; zh: string }> = {
    premium_income: { en: 'Premium Income', zh: '期权费收益' },
    trend_match: { en: 'Trend Match', zh: '趋势匹配度' },
    resistance_strength: { en: 'Resistance Strength', zh: '阻力位强度' },
    support_strength: { en: 'Support Strength', zh: '支撑位强度' },
    atr_safety: { en: 'ATR Safety', zh: 'ATR安全性' },
    liquidity: { en: 'Liquidity', zh: '流动性' },
    time_value: { en: 'Time Value', zh: '时间价值' },
    volatility: { en: 'Volatility', zh: '波动率' },
    risk_reward: { en: 'Risk/Reward', zh: '风险收益比' },
    momentum: { en: 'Momentum', zh: '动量' },
    breakout_potential: { en: 'Breakout Potential', zh: '突破潜力' },
};

export default function ReverseScore() {
    const { user, loading: authLoading } = useAuth();
    const navigate = useNavigate();
    const { i18n } = useTranslation();
    const isZh = i18n.language.startsWith('zh');

    // Input mode: 'upload' or 'manual' - default to manual (primary action)
    const [inputMode, setInputMode] = useState<'upload' | 'manual'>('manual');

    // Image upload state
    const [selectedImage, setSelectedImage] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [recognizing, setRecognizing] = useState(false);
    const [recognitionResult, setRecognitionResult] = useState<any>(null);
    const [recognitionError, setRecognitionError] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Form state
    const [symbol, setSymbol] = useState('');
    const [optionType, setOptionType] = useState<'CALL' | 'PUT'>('CALL');
    const [strike, setStrike] = useState('');
    const [expiryDate, setExpiryDate] = useState('');
    const [optionPrice, setOptionPrice] = useState('');
    const [impliedVolatility, setImpliedVolatility] = useState('');

    // Result state
    const [result, setResult] = useState<ReverseScoreResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Redirect if not authenticated
    useEffect(() => {
        if (!authLoading && !user) {
            navigate('/login');
        }
    }, [user, authLoading, navigate]);

    // Calculate score
    const handleCalculate = async () => {
        if (!symbol || !strike || !expiryDate || !optionPrice) {
            setError(isZh ? '请填写必填字段' : 'Please fill in required fields');
            return;
        }

        setLoading(true);
        setError('');
        setResult(null);

        try {
            const response = await api.post('/options/reverse-score', {
                symbol: symbol.toUpperCase(),
                option_type: optionType,
                strike: parseFloat(strike),
                expiry_date: expiryDate,
                option_price: parseFloat(optionPrice),
                implied_volatility: impliedVolatility ? parseFloat(impliedVolatility) : undefined
            });

            if (response.data.success) {
                setResult(response.data);
            } else {
                setError(response.data.error || (isZh ? '计算失败' : 'Calculation failed'));
            }
        } catch (err: any) {
            console.error('Reverse score error:', err);
            if (err.response?.status === 402) {
                setError(isZh ? '额度不足，请充值' : 'Insufficient credits, please top up');
            } else {
                setError(err.response?.data?.error || (isZh ? '请求失败' : 'Request failed'));
            }
        } finally {
            setLoading(false);
        }
    };

    // Handle image file selection
    const handleImageSelect = useCallback((file: File) => {
        // Validate file type
        const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            setRecognitionError(isZh ? '请上传 PNG、JPG 或 WebP 格式的图片' : 'Please upload PNG, JPG, or WebP images');
            return;
        }

        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            setRecognitionError(isZh ? '图片大小不能超过 10MB' : 'Image size cannot exceed 10MB');
            return;
        }

        setSelectedImage(file);
        setRecognitionError('');
        setRecognitionResult(null);

        // Create preview
        const reader = new FileReader();
        reader.onload = (e) => {
            setImagePreview(e.target?.result as string);
        };
        reader.readAsDataURL(file);
    }, [isZh]);

    // Handle drag events
    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) {
            handleImageSelect(file);
        }
    }, [handleImageSelect]);

    // Handle file input change
    const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleImageSelect(file);
        }
    }, [handleImageSelect]);

    // Handle image remove
    const handleRemoveImage = useCallback(() => {
        setSelectedImage(null);
        setImagePreview(null);
        setRecognitionResult(null);
        setRecognitionError('');
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    }, []);

    // Handle AI recognition
    const handleRecognize = async () => {
        if (!selectedImage) return;

        setRecognizing(true);
        setRecognitionError('');
        setRecognitionResult(null);

        try {
            const formData = new FormData();
            formData.append('image', selectedImage);

            const response = await api.post('/options/recognize-image', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            if (response.data.success) {
                setRecognitionResult(response.data.data);
                // Auto-fill form fields
                const data = response.data.data;
                if (data.symbol) setSymbol(data.symbol);
                if (data.option_type) setOptionType(data.option_type as 'CALL' | 'PUT');
                if (data.strike) setStrike(data.strike.toString());
                if (data.expiry_date) setExpiryDate(data.expiry_date);
                if (data.option_price) setOptionPrice(data.option_price.toString());
                if (data.implied_volatility) setImpliedVolatility(data.implied_volatility.toString());
            } else {
                setRecognitionError(response.data.error || (isZh ? '识别失败' : 'Recognition failed'));
            }
        } catch (err: any) {
            console.error('Recognition error:', err);
            setRecognitionError(err.response?.data?.error || (isZh ? '识别请求失败' : 'Recognition request failed'));
        } finally {
            setRecognizing(false);
        }
    };

    // Use recognition result and calculate score
    const handleUseRecognitionAndCalculate = async () => {
        if (recognitionResult) {
            // Form fields are already filled, just calculate
            await handleCalculate();
        }
    };

    // Get score class
    const getScoreClass = (score: number) => {
        if (score >= 70) return 'score-high';
        if (score >= 50) return 'score-medium';
        return 'score-low';
    };

    // Get strategy display name
    const getStrategyName = (key: string) => {
        const names: Record<string, { en: string; zh: string }> = {
            sell_call: { en: 'Sell Call', zh: '卖出看涨' },
            buy_call: { en: 'Buy Call', zh: '买入看涨' },
            sell_put: { en: 'Sell Put', zh: '卖出看跌' },
            buy_put: { en: 'Buy Put', zh: '买入看跌' },
        };
        return names[key] ? (isZh ? names[key].zh : names[key].en) : key;
    };

    // Format breakdown label
    const formatBreakdownLabel = (key: string) => {
        const label = breakdownLabels[key];
        if (label) {
            return isZh ? label.zh : label.en;
        }
        return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    };

    if (authLoading) {
        return (
            <div className="loading-overlay">
                <div className="spinner"></div>
                <span>{isZh ? '加载中...' : 'Loading...'}</span>
            </div>
        );
    }

    return (
        <>
            <style>{styles}</style>
            <div className="reverse-score-container">
                {/* Header */}
                <div className="header-section">
                    <h1 className="text-2xl font-bold mb-2">
                        {isZh ? '期权反向查分' : 'Option Reverse Score'}
                    </h1>
                    <p className="text-muted-foreground">
                        {isZh
                            ? '上传截图或手动输入期权参数，获取我们算法的评分和建议'
                            : 'Upload a screenshot or enter option parameters to get our algorithm\'s score and recommendations'}
                    </p>
                </div>

                {/* Input Mode - Manual input only (OCR hidden for now) */}
                <div className="form-card">
                    <div className="input-mode-tabs">
                        <button
                            className={`input-mode-tab active`}
                            onClick={() => setInputMode('manual')}
                        >
                            <FileText size={18} />
                            {isZh ? '手动录入' : 'Manual Input'}
                        </button>
                        {/* OCR截图识别功能暂时隐藏
                        <button
                            className={`input-mode-tab secondary ${inputMode === 'upload' ? 'active' : ''}`}
                            onClick={() => setInputMode('upload')}
                        >
                            <Camera size={14} />
                            {isZh ? '截图识别' : 'Screenshot'}
                        </button>
                        */}
                    </div>

                    {/* Image Upload Mode */}
                    {inputMode === 'upload' && (
                        <div className="mb-4">
                            <input
                                type="file"
                                ref={fileInputRef}
                                accept="image/png,image/jpeg,image/jpg,image/webp"
                                onChange={handleFileInputChange}
                                className="hidden"
                            />

                            {!imagePreview ? (
                                <div
                                    className={`image-upload-area ${isDragging ? 'dragging' : ''}`}
                                    onClick={() => fileInputRef.current?.click()}
                                    onDragOver={handleDragOver}
                                    onDragLeave={handleDragLeave}
                                    onDrop={handleDrop}
                                >
                                    <Upload className="upload-icon" />
                                    <p className="upload-text">
                                        {isZh
                                            ? '点击上传或拖拽图片到这里'
                                            : 'Click to upload or drag and drop'}
                                    </p>
                                    <p className="upload-hint">
                                        {isZh
                                            ? '支持 PNG、JPG、WebP 格式，最大 10MB'
                                            : 'PNG, JPG, WebP up to 10MB'}
                                    </p>
                                </div>
                            ) : (
                                <div className="text-center">
                                    <div className="image-preview-container">
                                        <img src={imagePreview} alt="Preview" className="image-preview" />
                                        <button
                                            className="image-remove-btn"
                                            onClick={handleRemoveImage}
                                            title={isZh ? '移除图片' : 'Remove image'}
                                        >
                                            <X size={16} />
                                        </button>
                                    </div>

                                    {/* Recognition Button */}
                                    {!recognitionResult && !recognitionError && (
                                        <div className="mt-4">
                                            <Button
                                                onClick={handleRecognize}
                                                disabled={recognizing}
                                                className="w-full max-w-xs"
                                            >
                                                {recognizing ? (
                                                    <>
                                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                                        {isZh ? 'AI识别中...' : 'Recognizing...'}
                                                    </>
                                                ) : (
                                                    <>
                                                        <Camera className="mr-2 h-4 w-4" />
                                                        {isZh ? 'AI识别期权参数' : 'AI Recognize Parameters'}
                                                    </>
                                                )}
                                            </Button>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Recognition Error */}
                            {recognitionError && (
                                <div className="recognition-result error">
                                    <div className="recognition-result-header">
                                        <X size={18} />
                                        {isZh ? '识别失败' : 'Recognition Failed'}
                                    </div>
                                    <p className="text-sm">{recognitionError}</p>
                                    <div className="recognition-actions">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={handleRecognize}
                                            disabled={recognizing}
                                        >
                                            {isZh ? '重试' : 'Retry'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => setInputMode('manual')}
                                        >
                                            {isZh ? '手动录入' : 'Manual Input'}
                                        </Button>
                                    </div>
                                </div>
                            )}

                            {/* Recognition Result */}
                            {recognitionResult && (
                                <div className="recognition-result">
                                    <div className="recognition-result-header">
                                        <Camera size={18} />
                                        {isZh ? '识别成功' : 'Recognition Successful'}
                                        {recognitionResult.confidence && (
                                            <span className="text-xs ml-2 opacity-70">
                                                ({isZh ? '置信度' : 'Confidence'}: {recognitionResult.confidence})
                                            </span>
                                        )}
                                    </div>
                                    <div className="recognition-fields">
                                        <div className="recognition-field">
                                            <span className="recognition-field-label">{isZh ? '股票代码' : 'Symbol'}</span>
                                            <span className="recognition-field-value">{recognitionResult.symbol}</span>
                                        </div>
                                        <div className="recognition-field">
                                            <span className="recognition-field-label">{isZh ? '期权类型' : 'Type'}</span>
                                            <span className="recognition-field-value">{recognitionResult.option_type}</span>
                                        </div>
                                        <div className="recognition-field">
                                            <span className="recognition-field-label">{isZh ? '执行价' : 'Strike'}</span>
                                            <span className="recognition-field-value">${recognitionResult.strike}</span>
                                        </div>
                                        <div className="recognition-field">
                                            <span className="recognition-field-label">{isZh ? '到期日' : 'Expiry'}</span>
                                            <span className="recognition-field-value">{recognitionResult.expiry_date}</span>
                                        </div>
                                        <div className="recognition-field">
                                            <span className="recognition-field-label">{isZh ? '期权价格' : 'Price'}</span>
                                            <span className="recognition-field-value">${recognitionResult.option_price}</span>
                                        </div>
                                        {recognitionResult.implied_volatility && (
                                            <div className="recognition-field">
                                                <span className="recognition-field-label">{isZh ? '隐含波动率' : 'IV'}</span>
                                                <span className="recognition-field-value">{(recognitionResult.implied_volatility * 100).toFixed(1)}%</span>
                                            </div>
                                        )}
                                    </div>
                                    {recognitionResult.notes && (
                                        <p className="text-xs text-muted-foreground mt-2">{recognitionResult.notes}</p>
                                    )}
                                    <div className="recognition-actions">
                                        <Button
                                            onClick={handleUseRecognitionAndCalculate}
                                            disabled={loading}
                                            className="flex-1"
                                        >
                                            {loading
                                                ? (isZh ? '计算中...' : 'Calculating...')
                                                : (isZh ? '计算评分' : 'Calculate Score')}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            onClick={() => setInputMode('manual')}
                                        >
                                            {isZh ? '编辑参数' : 'Edit Parameters'}
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Manual Input Mode */}
                    {inputMode === 'manual' && (
                    <div className="form-grid">
                        {/* Symbol */}
                        <div className="form-group">
                            <label className="form-label">
                                {isZh ? '股票代码' : 'Stock Symbol'} *
                            </label>
                            <StockSearchInput
                                value={symbol}
                                onChange={setSymbol}
                                placeholder={isZh ? '输入股票代码' : 'Enter ticker'}
                            />
                        </div>

                        {/* Option Type */}
                        <div className="form-group">
                            <label className="form-label">
                                {isZh ? '期权类型' : 'Option Type'} *
                            </label>
                            <div className="option-type-toggle">
                                <button
                                    className={`option-type-btn call ${optionType === 'CALL' ? 'active' : ''}`}
                                    onClick={() => setOptionType('CALL')}
                                >
                                    CALL
                                </button>
                                <button
                                    className={`option-type-btn put ${optionType === 'PUT' ? 'active' : ''}`}
                                    onClick={() => setOptionType('PUT')}
                                >
                                    PUT
                                </button>
                            </div>
                        </div>

                        {/* Strike */}
                        <div className="form-group">
                            <label className="form-label">
                                {isZh ? '执行价' : 'Strike Price'} *
                            </label>
                            <input
                                type="number"
                                className="form-input"
                                value={strike}
                                onChange={(e) => setStrike(e.target.value)}
                                placeholder={isZh ? '例如: 190' : 'e.g., 190'}
                                step="0.5"
                            />
                        </div>

                        {/* Expiry Date */}
                        <div className="form-group">
                            <label className="form-label">
                                {isZh ? '到期日' : 'Expiry Date'} *
                            </label>
                            <input
                                type="date"
                                className="form-input"
                                value={expiryDate}
                                onChange={(e) => setExpiryDate(e.target.value)}
                            />
                        </div>

                        {/* Option Price */}
                        <div className="form-group">
                            <label className="form-label">
                                {isZh ? '期权价格' : 'Option Price'} *
                            </label>
                            <input
                                type="number"
                                className="form-input"
                                value={optionPrice}
                                onChange={(e) => setOptionPrice(e.target.value)}
                                placeholder={isZh ? 'Bid/Ask中间价' : 'Mid price'}
                                step="0.01"
                            />
                        </div>

                        {/* Implied Volatility */}
                        <div className="form-group">
                            <label className="form-label">
                                {isZh ? '隐含波动率 (可选)' : 'Implied Volatility (optional)'}
                            </label>
                            <input
                                type="number"
                                className="form-input"
                                value={impliedVolatility}
                                onChange={(e) => setImpliedVolatility(e.target.value)}
                                placeholder={isZh ? '例如: 0.28 (留空自动估算)' : 'e.g., 0.28 (auto-estimate if empty)'}
                                step="0.01"
                            />
                        </div>

                        {/* Submit Button */}
                        <div className="form-group full-width">
                            <Button
                                onClick={handleCalculate}
                                disabled={loading}
                                className="w-full py-3 text-lg"
                            >
                                {loading
                                    ? (isZh ? '计算中...' : 'Calculating...')
                                    : (isZh ? '计算评分' : 'Calculate Score')}
                            </Button>
                        </div>
                    </div>
                    )}
                </div>

                {/* Error */}
                {error && (
                    <div className="error-message mb-4">
                        {error}
                    </div>
                )}

                {/* Loading */}
                {loading && (
                    <div className="form-card">
                        <div className="loading-overlay">
                            <div className="spinner"></div>
                            <span>{isZh ? '正在分析期权数据...' : 'Analyzing option data...'}</span>
                        </div>
                    </div>
                )}

                {/* Results */}
                {result && !loading && (
                    <>
                        {/* Stock Info */}
                        <div className="form-card">
                            <h3 className="text-lg font-semibold mb-3">
                                {result.symbol} - {result.option_type} ${result.strike} ({result.expiry_date})
                            </h3>
                            <div className="stock-info">
                                <div className="stock-info-item">
                                    <div className="stock-info-label">
                                        {isZh ? '当前股价' : 'Current Price'}
                                    </div>
                                    <div className="stock-info-value">
                                        ${result.current_price?.toFixed(2) || '-'}
                                    </div>
                                </div>
                                {result.trend_info && (
                                    <>
                                        <div className="stock-info-item">
                                            <div className="stock-info-label">
                                                {isZh ? '趋势' : 'Trend'}
                                            </div>
                                            <div className="stock-info-value">
                                                {result.trend_info.trend === 'uptrend' ? (isZh ? '上升' : 'Up') :
                                                 result.trend_info.trend === 'downtrend' ? (isZh ? '下降' : 'Down') :
                                                 (isZh ? '横盘' : 'Sideways')}
                                            </div>
                                        </div>
                                        <div className="stock-info-item">
                                            <div className="stock-info-label">
                                                {isZh ? '趋势强度' : 'Strength'}
                                            </div>
                                            <div className="stock-info-value">
                                                {((result.trend_info.trend_strength || 0) * 100).toFixed(0)}%
                                            </div>
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Score Results */}
                        {Object.entries(result.scores).map(([strategy, scoreData]) => {
                            if (!scoreData) return null;
                            return (
                                <div key={strategy} className="result-card">
                                    <div className="result-header">
                                        <div>
                                            <span className="strategy-name">
                                                {getStrategyName(strategy)}
                                            </span>
                                            <div
                                                className="style-badge"
                                                style={{
                                                    backgroundColor: `${scoreData.risk_color}20`,
                                                    color: scoreData.risk_color
                                                }}
                                            >
                                                {scoreData.style_label}
                                            </div>
                                        </div>
                                        <div className={`score-badge ${getScoreClass(scoreData.score)}`}>
                                            {scoreData.score.toFixed(0)}
                                        </div>
                                    </div>

                                    {/* Risk Metrics */}
                                    {(scoreData.win_probability || scoreData.max_profit_pct || scoreData.max_loss_pct) && (
                                        <div className="flex gap-6 mb-4 text-sm">
                                            {scoreData.win_probability && (
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        {isZh ? '胜率: ' : 'Win Rate: '}
                                                    </span>
                                                    <span className="font-medium">
                                                        {(scoreData.win_probability * 100).toFixed(0)}%
                                                    </span>
                                                </div>
                                            )}
                                            {scoreData.max_profit_pct && (
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        {isZh ? '最大收益: ' : 'Max Profit: '}
                                                    </span>
                                                    <span className="font-medium text-green-500">
                                                        +{(scoreData.max_profit_pct * 100).toFixed(1)}%
                                                    </span>
                                                </div>
                                            )}
                                            {scoreData.max_loss_pct && (
                                                <div>
                                                    <span className="text-muted-foreground">
                                                        {isZh ? '最大损失: ' : 'Max Loss: '}
                                                    </span>
                                                    <span className="font-medium text-red-500">
                                                        {(scoreData.max_loss_pct * 100).toFixed(1)}%
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Score Breakdown */}
                                    <h4 className="text-sm font-medium text-muted-foreground mb-2">
                                        {isZh ? '评分明细' : 'Score Breakdown'}
                                    </h4>
                                    <div className="breakdown-grid">
                                        {Object.entries(scoreData.breakdown || {}).map(([key, value]) => {
                                            if (value === undefined || value === null) return null;
                                            return (
                                                <div key={key} className="breakdown-item">
                                                    <span className="breakdown-label">
                                                        {formatBreakdownLabel(key)}
                                                    </span>
                                                    <span className={`breakdown-score ${
                                                        value >= 70 ? 'text-green-500' :
                                                        value >= 50 ? 'text-yellow-500' :
                                                        'text-red-500'
                                                    }`}>
                                                        {typeof value === 'number' ? value.toFixed(0) : value}
                                                    </span>
                                                </div>
                                            );
                                        })}
                                    </div>

                                    {/* Trend Warning */}
                                    {scoreData.trend_warning && (
                                        <div className="trend-warning">
                                            {scoreData.trend_warning}
                                        </div>
                                    )}
                                </div>
                            );
                        })}

                        {/* Action Buttons */}
                        <div className="form-card">
                            <div className="flex gap-4 justify-center">
                                <Button
                                    variant="outline"
                                    onClick={() => navigate(`/stock?ticker=${result.symbol}`)}
                                >
                                    {isZh ? '查看股票分析' : 'View Stock Analysis'}
                                </Button>
                                <Button
                                    variant="outline"
                                    onClick={() => navigate(`/options?ticker=${result.symbol}`)}
                                >
                                    {isZh ? '查看期权链' : 'View Options Chain'}
                                </Button>
                            </div>
                        </div>
                    </>
                )}

                {/* Marketing Section */}
                <div className="form-card mt-8 border-t border-slate-700 pt-6">
                    <div className="text-center">
                        <h3 className="text-lg font-semibold mb-2">
                            {isZh ? '探索更多期权机会' : 'Explore More Options Opportunities'}
                        </h3>
                        <p className="text-sm text-muted-foreground mb-4 max-w-lg mx-auto">
                            {isZh
                                ? '使用我们的AI期权研究工具，发现市场上最优质的期权交易机会'
                                : 'Use our AI options research tool to discover the best options trading opportunities'}
                        </p>
                        <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground mb-4">
                            <span className="px-2 py-1 bg-slate-800 rounded">
                                {isZh ? '智能期权链分析' : 'Smart Options Chain'}
                            </span>
                            <span className="px-2 py-1 bg-slate-800 rounded">
                                {isZh ? '每日热门推荐' : 'Daily Hot Picks'}
                            </span>
                            <span className="px-2 py-1 bg-slate-800 rounded">
                                {isZh ? '风险评估' : 'Risk Assessment'}
                            </span>
                        </div>
                        <Button
                            onClick={() => navigate('/options')}
                            className="bg-[#0D9B97] hover:bg-[#10B5B0] text-white"
                        >
                            {isZh ? '立即体验期权研究' : 'Try Options Research Now'}
                        </Button>
                    </div>
                </div>
            </div>
        </>
    );
}
