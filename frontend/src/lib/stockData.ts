// Stock data with ticker, Chinese name, English name, and pinyin initials
export interface StockInfo {
    ticker: string;
    nameCn: string;
    nameEn: string;
    pinyin: string;  // Pinyin initials
    market: 'US' | 'HK' | 'CN';
}

// Common US stocks
export const US_STOCKS: StockInfo[] = [
    // Tech Giants
    { ticker: 'AAPL', nameCn: '苹果', nameEn: 'Apple', pinyin: 'pg', market: 'US' },
    { ticker: 'MSFT', nameCn: '微软', nameEn: 'Microsoft', pinyin: 'wr', market: 'US' },
    { ticker: 'GOOGL', nameCn: '谷歌', nameEn: 'Google/Alphabet', pinyin: 'gg', market: 'US' },
    { ticker: 'GOOG', nameCn: '谷歌C类', nameEn: 'Google Class C', pinyin: 'ggcl', market: 'US' },
    { ticker: 'AMZN', nameCn: '亚马逊', nameEn: 'Amazon', pinyin: 'ymx', market: 'US' },
    { ticker: 'META', nameCn: '脸书/Meta', nameEn: 'Meta/Facebook', pinyin: 'ls', market: 'US' },
    { ticker: 'NVDA', nameCn: '英伟达', nameEn: 'NVIDIA', pinyin: 'ywd', market: 'US' },
    { ticker: 'TSLA', nameCn: '特斯拉', nameEn: 'Tesla', pinyin: 'tsl', market: 'US' },
    { ticker: 'AMD', nameCn: '超威半导体', nameEn: 'AMD', pinyin: 'cwbdt', market: 'US' },
    { ticker: 'INTC', nameCn: '英特尔', nameEn: 'Intel', pinyin: 'yte', market: 'US' },
    { ticker: 'NFLX', nameCn: '奈飞', nameEn: 'Netflix', pinyin: 'nf', market: 'US' },
    { ticker: 'CRM', nameCn: '赛富时', nameEn: 'Salesforce', pinyin: 'sfs', market: 'US' },
    { ticker: 'ORCL', nameCn: '甲骨文', nameEn: 'Oracle', pinyin: 'jgw', market: 'US' },
    { ticker: 'ADBE', nameCn: '奥多比', nameEn: 'Adobe', pinyin: 'adb', market: 'US' },
    { ticker: 'CSCO', nameCn: '思科', nameEn: 'Cisco', pinyin: 'sk', market: 'US' },
    { ticker: 'AVGO', nameCn: '博通', nameEn: 'Broadcom', pinyin: 'bt', market: 'US' },
    { ticker: 'QCOM', nameCn: '高通', nameEn: 'Qualcomm', pinyin: 'gt', market: 'US' },
    { ticker: 'TXN', nameCn: '德州仪器', nameEn: 'Texas Instruments', pinyin: 'dzyq', market: 'US' },
    { ticker: 'IBM', nameCn: '国际商业机器', nameEn: 'IBM', pinyin: 'gjsyjq', market: 'US' },
    { ticker: 'MU', nameCn: '美光科技', nameEn: 'Micron', pinyin: 'mgkj', market: 'US' },

    // Finance
    { ticker: 'JPM', nameCn: '摩根大通', nameEn: 'JPMorgan', pinyin: 'mgdt', market: 'US' },
    { ticker: 'BAC', nameCn: '美国银行', nameEn: 'Bank of America', pinyin: 'mgyh', market: 'US' },
    { ticker: 'WFC', nameCn: '富国银行', nameEn: 'Wells Fargo', pinyin: 'fgyh', market: 'US' },
    { ticker: 'GS', nameCn: '高盛', nameEn: 'Goldman Sachs', pinyin: 'gs', market: 'US' },
    { ticker: 'MS', nameCn: '摩根士丹利', nameEn: 'Morgan Stanley', pinyin: 'mgsdl', market: 'US' },
    { ticker: 'C', nameCn: '花旗', nameEn: 'Citigroup', pinyin: 'hq', market: 'US' },
    { ticker: 'V', nameCn: '维萨', nameEn: 'Visa', pinyin: 'ws', market: 'US' },
    { ticker: 'MA', nameCn: '万事达', nameEn: 'Mastercard', pinyin: 'wsd', market: 'US' },
    { ticker: 'PYPL', nameCn: '贝宝', nameEn: 'PayPal', pinyin: 'bb', market: 'US' },
    { ticker: 'AXP', nameCn: '美国运通', nameEn: 'American Express', pinyin: 'mgyt', market: 'US' },
    { ticker: 'BRK.B', nameCn: '伯克希尔B', nameEn: 'Berkshire B', pinyin: 'bkxe', market: 'US' },
    { ticker: 'SCHW', nameCn: '嘉信理财', nameEn: 'Charles Schwab', pinyin: 'jxlc', market: 'US' },

    // Consumer
    { ticker: 'WMT', nameCn: '沃尔玛', nameEn: 'Walmart', pinyin: 'wem', market: 'US' },
    { ticker: 'COST', nameCn: '开市客', nameEn: 'Costco', pinyin: 'ksk', market: 'US' },
    { ticker: 'HD', nameCn: '家得宝', nameEn: 'Home Depot', pinyin: 'jdb', market: 'US' },
    { ticker: 'TGT', nameCn: '塔吉特', nameEn: 'Target', pinyin: 'tjt', market: 'US' },
    { ticker: 'LOW', nameCn: '劳氏', nameEn: "Lowe's", pinyin: 'ls', market: 'US' },
    { ticker: 'NKE', nameCn: '耐克', nameEn: 'Nike', pinyin: 'nk', market: 'US' },
    { ticker: 'SBUX', nameCn: '星巴克', nameEn: 'Starbucks', pinyin: 'xbk', market: 'US' },
    { ticker: 'MCD', nameCn: '麦当劳', nameEn: "McDonald's", pinyin: 'mdl', market: 'US' },
    { ticker: 'DIS', nameCn: '迪士尼', nameEn: 'Disney', pinyin: 'dsn', market: 'US' },
    { ticker: 'KO', nameCn: '可口可乐', nameEn: 'Coca-Cola', pinyin: 'kkkl', market: 'US' },
    { ticker: 'PEP', nameCn: '百事可乐', nameEn: 'PepsiCo', pinyin: 'bskl', market: 'US' },
    { ticker: 'PG', nameCn: '宝洁', nameEn: 'Procter & Gamble', pinyin: 'bj', market: 'US' },

    // Healthcare
    { ticker: 'JNJ', nameCn: '强生', nameEn: 'Johnson & Johnson', pinyin: 'qs', market: 'US' },
    { ticker: 'UNH', nameCn: '联合健康', nameEn: 'UnitedHealth', pinyin: 'lhjk', market: 'US' },
    { ticker: 'PFE', nameCn: '辉瑞', nameEn: 'Pfizer', pinyin: 'hr', market: 'US' },
    { ticker: 'MRK', nameCn: '默沙东', nameEn: 'Merck', pinyin: 'msd', market: 'US' },
    { ticker: 'ABBV', nameCn: '艾伯维', nameEn: 'AbbVie', pinyin: 'abw', market: 'US' },
    { ticker: 'LLY', nameCn: '礼来', nameEn: 'Eli Lilly', pinyin: 'll', market: 'US' },
    { ticker: 'TMO', nameCn: '赛默飞世尔', nameEn: 'Thermo Fisher', pinyin: 'smfse', market: 'US' },
    { ticker: 'ABT', nameCn: '雅培', nameEn: 'Abbott', pinyin: 'yp', market: 'US' },
    { ticker: 'BMY', nameCn: '百时美施贵宝', nameEn: 'Bristol-Myers', pinyin: 'bsmsgb', market: 'US' },
    { ticker: 'AMGN', nameCn: '安进', nameEn: 'Amgen', pinyin: 'aj', market: 'US' },
    { ticker: 'GILD', nameCn: '吉利德', nameEn: 'Gilead', pinyin: 'jld', market: 'US' },
    { ticker: 'MRNA', nameCn: '莫德纳', nameEn: 'Moderna', pinyin: 'mdn', market: 'US' },

    // Energy
    { ticker: 'XOM', nameCn: '埃克森美孚', nameEn: 'Exxon Mobil', pinyin: 'aksmmf', market: 'US' },
    { ticker: 'CVX', nameCn: '雪佛龙', nameEn: 'Chevron', pinyin: 'xfl', market: 'US' },
    { ticker: 'COP', nameCn: '康菲石油', nameEn: 'ConocoPhillips', pinyin: 'kfsy', market: 'US' },
    { ticker: 'SLB', nameCn: '斯伦贝谢', nameEn: 'Schlumberger', pinyin: 'slbx', market: 'US' },
    { ticker: 'EOG', nameCn: 'EOG资源', nameEn: 'EOG Resources', pinyin: 'eogzy', market: 'US' },

    // Industrial
    { ticker: 'CAT', nameCn: '卡特彼勒', nameEn: 'Caterpillar', pinyin: 'ktbl', market: 'US' },
    { ticker: 'BA', nameCn: '波音', nameEn: 'Boeing', pinyin: 'by', market: 'US' },
    { ticker: 'HON', nameCn: '霍尼韦尔', nameEn: 'Honeywell', pinyin: 'hnwe', market: 'US' },
    { ticker: 'UPS', nameCn: '联合包裹', nameEn: 'UPS', pinyin: 'lhbg', market: 'US' },
    { ticker: 'RTX', nameCn: '雷神技术', nameEn: 'Raytheon', pinyin: 'lsjs', market: 'US' },
    { ticker: 'LMT', nameCn: '洛克希德马丁', nameEn: 'Lockheed Martin', pinyin: 'lkxdmd', market: 'US' },
    { ticker: 'GE', nameCn: '通用电气', nameEn: 'General Electric', pinyin: 'tydq', market: 'US' },
    { ticker: 'MMM', nameCn: '3M公司', nameEn: '3M', pinyin: '3mgs', market: 'US' },
    { ticker: 'DE', nameCn: '迪尔', nameEn: 'Deere', pinyin: 'de', market: 'US' },

    // Communication
    { ticker: 'T', nameCn: '美国电话电报', nameEn: 'AT&T', pinyin: 'mgdhdb', market: 'US' },
    { ticker: 'VZ', nameCn: '威瑞森', nameEn: 'Verizon', pinyin: 'wrs', market: 'US' },
    { ticker: 'TMUS', nameCn: 'T-Mobile美国', nameEn: 'T-Mobile', pinyin: 'tmobilemg', market: 'US' },
    { ticker: 'CMCSA', nameCn: '康卡斯特', nameEn: 'Comcast', pinyin: 'kkst', market: 'US' },

    // Chinese ADRs
    { ticker: 'BABA', nameCn: '阿里巴巴', nameEn: 'Alibaba', pinyin: 'albb', market: 'US' },
    { ticker: 'JD', nameCn: '京东', nameEn: 'JD.com', pinyin: 'jd', market: 'US' },
    { ticker: 'PDD', nameCn: '拼多多', nameEn: 'Pinduoduo', pinyin: 'pdd', market: 'US' },
    { ticker: 'BIDU', nameCn: '百度', nameEn: 'Baidu', pinyin: 'bd', market: 'US' },
    { ticker: 'NIO', nameCn: '蔚来', nameEn: 'NIO', pinyin: 'wl', market: 'US' },
    { ticker: 'XPEV', nameCn: '小鹏汽车', nameEn: 'XPeng', pinyin: 'xpqc', market: 'US' },
    { ticker: 'LI', nameCn: '理想汽车', nameEn: 'Li Auto', pinyin: 'lxqc', market: 'US' },
    { ticker: 'BILI', nameCn: '哔哩哔哩', nameEn: 'Bilibili', pinyin: 'blbl', market: 'US' },
    { ticker: 'TME', nameCn: '腾讯音乐', nameEn: 'Tencent Music', pinyin: 'txyy', market: 'US' },
    { ticker: 'NTES', nameCn: '网易', nameEn: 'NetEase', pinyin: 'wy', market: 'US' },
    { ticker: 'ZTO', nameCn: '中通快递', nameEn: 'ZTO Express', pinyin: 'ztkd', market: 'US' },
    { ticker: 'TCOM', nameCn: '携程', nameEn: 'Trip.com', pinyin: 'xc', market: 'US' },
    { ticker: 'TAL', nameCn: '好未来', nameEn: 'TAL Education', pinyin: 'hwl', market: 'US' },
    { ticker: 'EDU', nameCn: '新东方', nameEn: 'New Oriental', pinyin: 'xdf', market: 'US' },
    { ticker: 'IQ', nameCn: '爱奇艺', nameEn: 'iQIYI', pinyin: 'aqy', market: 'US' },
    { ticker: 'WB', nameCn: '微博', nameEn: 'Weibo', pinyin: 'wb', market: 'US' },
    { ticker: 'FUTU', nameCn: '富途', nameEn: 'Futu', pinyin: 'ft', market: 'US' },

    // ETFs
    { ticker: 'SPY', nameCn: '标普500ETF', nameEn: 'S&P 500 ETF', pinyin: 'bp500etf', market: 'US' },
    { ticker: 'QQQ', nameCn: '纳指100ETF', nameEn: 'Nasdaq 100 ETF', pinyin: 'nz100etf', market: 'US' },
    { ticker: 'IWM', nameCn: '罗素2000ETF', nameEn: 'Russell 2000 ETF', pinyin: 'ls2000etf', market: 'US' },
    { ticker: 'VTI', nameCn: '美股全市场ETF', nameEn: 'Total Market ETF', pinyin: 'mgqscetf', market: 'US' },
    { ticker: 'ARKK', nameCn: 'ARK创新ETF', nameEn: 'ARK Innovation ETF', pinyin: 'arkcxetf', market: 'US' },
    { ticker: 'XLF', nameCn: '金融精选ETF', nameEn: 'Financial ETF', pinyin: 'jrjxetf', market: 'US' },
    { ticker: 'XLE', nameCn: '能源精选ETF', nameEn: 'Energy ETF', pinyin: 'nyjxetf', market: 'US' },
    { ticker: 'XLK', nameCn: '科技精选ETF', nameEn: 'Technology ETF', pinyin: 'kjjxetf', market: 'US' },
    { ticker: 'SOXX', nameCn: '半导体ETF', nameEn: 'Semiconductor ETF', pinyin: 'bdtetf', market: 'US' },
    { ticker: 'TLT', nameCn: '20年期国债ETF', nameEn: '20+ Year Treasury ETF', pinyin: '20ngzetf', market: 'US' },
    { ticker: 'GLD', nameCn: '黄金ETF', nameEn: 'Gold ETF', pinyin: 'hjetf', market: 'US' },
    { ticker: 'SLV', nameCn: '白银ETF', nameEn: 'Silver ETF', pinyin: 'byetf', market: 'US' },
    { ticker: 'USO', nameCn: '原油ETF', nameEn: 'Oil ETF', pinyin: 'yyetf', market: 'US' },
    { ticker: 'VNQ', nameCn: '房地产ETF', nameEn: 'Real Estate ETF', pinyin: 'fdcetf', market: 'US' },
    { ticker: 'EEM', nameCn: '新兴市场ETF', nameEn: 'Emerging Markets ETF', pinyin: 'xxscetf', market: 'US' },
    { ticker: 'FXI', nameCn: '中国大盘股ETF', nameEn: 'China Large-Cap ETF', pinyin: 'zgdpgetf', market: 'US' },
    { ticker: 'KWEB', nameCn: '中国互联网ETF', nameEn: 'China Internet ETF', pinyin: 'zghlwetf', market: 'US' },
];

// Hong Kong stocks
export const HK_STOCKS: StockInfo[] = [
    { ticker: '0700.HK', nameCn: '腾讯控股', nameEn: 'Tencent', pinyin: 'txkg', market: 'HK' },
    { ticker: '9988.HK', nameCn: '阿里巴巴-SW', nameEn: 'Alibaba-SW', pinyin: 'albb', market: 'HK' },
    { ticker: '3690.HK', nameCn: '美团-W', nameEn: 'Meituan', pinyin: 'mt', market: 'HK' },
    { ticker: '9618.HK', nameCn: '京东集团-SW', nameEn: 'JD-SW', pinyin: 'jdjt', market: 'HK' },
    { ticker: '9999.HK', nameCn: '网易-S', nameEn: 'NetEase-S', pinyin: 'wy', market: 'HK' },
    { ticker: '1810.HK', nameCn: '小米集团-W', nameEn: 'Xiaomi', pinyin: 'xmjt', market: 'HK' },
    { ticker: '2020.HK', nameCn: '安踏体育', nameEn: 'ANTA Sports', pinyin: 'atty', market: 'HK' },
    { ticker: '0941.HK', nameCn: '中国移动', nameEn: 'China Mobile', pinyin: 'zgyd', market: 'HK' },
    { ticker: '0005.HK', nameCn: '汇丰控股', nameEn: 'HSBC', pinyin: 'hfkg', market: 'HK' },
    { ticker: '0388.HK', nameCn: '香港交易所', nameEn: 'HKEX', pinyin: 'xgjys', market: 'HK' },
    { ticker: '1299.HK', nameCn: '友邦保险', nameEn: 'AIA', pinyin: 'ybbx', market: 'HK' },
    { ticker: '0939.HK', nameCn: '建设银行', nameEn: 'CCB', pinyin: 'jsyh', market: 'HK' },
    { ticker: '1398.HK', nameCn: '工商银行', nameEn: 'ICBC', pinyin: 'gsyh', market: 'HK' },
    { ticker: '2318.HK', nameCn: '中国平安', nameEn: 'Ping An', pinyin: 'zgpa', market: 'HK' },
    { ticker: '0883.HK', nameCn: '中国海洋石油', nameEn: 'CNOOC', pinyin: 'zghysy', market: 'HK' },
    { ticker: '0857.HK', nameCn: '中国石油股份', nameEn: 'PetroChina', pinyin: 'zgsy', market: 'HK' },
    { ticker: '9888.HK', nameCn: '百度集团-SW', nameEn: 'Baidu-SW', pinyin: 'bdjt', market: 'HK' },
    { ticker: '9961.HK', nameCn: '携程集团-S', nameEn: 'Trip.com', pinyin: 'xcjt', market: 'HK' },
    { ticker: '9626.HK', nameCn: '哔哩哔哩-SW', nameEn: 'Bilibili-SW', pinyin: 'blbl', market: 'HK' },
    { ticker: '2015.HK', nameCn: '理想汽车-W', nameEn: 'Li Auto-W', pinyin: 'lxqc', market: 'HK' },
    { ticker: '9866.HK', nameCn: '蔚来-SW', nameEn: 'NIO-SW', pinyin: 'wl', market: 'HK' },
    { ticker: '9868.HK', nameCn: '小鹏汽车-W', nameEn: 'XPeng-W', pinyin: 'xpqc', market: 'HK' },
    { ticker: '1024.HK', nameCn: '快手-W', nameEn: 'Kuaishou', pinyin: 'ks', market: 'HK' },
    { ticker: '2382.HK', nameCn: '舜宇光学科技', nameEn: 'Sunny Optical', pinyin: 'sygxkj', market: 'HK' },
    { ticker: '0981.HK', nameCn: '中芯国际', nameEn: 'SMIC', pinyin: 'zxgj', market: 'HK' },
];

// China A-shares (simplified list)
export const CN_STOCKS: StockInfo[] = [
    { ticker: '600519.SS', nameCn: '贵州茅台', nameEn: 'Kweichow Moutai', pinyin: 'gzmt', market: 'CN' },
    { ticker: '000858.SZ', nameCn: '五粮液', nameEn: 'Wuliangye', pinyin: 'wly', market: 'CN' },
    { ticker: '601318.SS', nameCn: '中国平安', nameEn: 'Ping An', pinyin: 'zgpa', market: 'CN' },
    { ticker: '600036.SS', nameCn: '招商银行', nameEn: 'CMB', pinyin: 'zsyh', market: 'CN' },
    { ticker: '000333.SZ', nameCn: '美的集团', nameEn: 'Midea', pinyin: 'mdjt', market: 'CN' },
    { ticker: '000651.SZ', nameCn: '格力电器', nameEn: 'Gree Electric', pinyin: 'gldq', market: 'CN' },
    { ticker: '601888.SS', nameCn: '中国中免', nameEn: 'China Tourism', pinyin: 'zgzm', market: 'CN' },
    { ticker: '300750.SZ', nameCn: '宁德时代', nameEn: 'CATL', pinyin: 'ndsd', market: 'CN' },
    { ticker: '002594.SZ', nameCn: '比亚迪', nameEn: 'BYD', pinyin: 'byd', market: 'CN' },
    { ticker: '600276.SS', nameCn: '恒瑞医药', nameEn: 'Hengrui', pinyin: 'hryy', market: 'CN' },
    { ticker: '000001.SZ', nameCn: '平安银行', nameEn: 'Ping An Bank', pinyin: 'payh', market: 'CN' },
    { ticker: '601166.SS', nameCn: '兴业银行', nameEn: 'Industrial Bank', pinyin: 'xyyh', market: 'CN' },
    { ticker: '600900.SS', nameCn: '长江电力', nameEn: 'Yangtze Power', pinyin: 'cjdl', market: 'CN' },
    { ticker: '601012.SS', nameCn: '隆基绿能', nameEn: 'LONGi Green', pinyin: 'ljln', market: 'CN' },
    { ticker: '002415.SZ', nameCn: '海康威视', nameEn: 'Hikvision', pinyin: 'hkws', market: 'CN' },
    { ticker: '600809.SS', nameCn: '山西汾酒', nameEn: 'Shanxi Fenjiu', pinyin: 'sxfj', market: 'CN' },
    { ticker: '000568.SZ', nameCn: '泸州老窖', nameEn: 'Luzhou Laojiao', pinyin: 'lzlj', market: 'CN' },
    { ticker: '603259.SS', nameCn: '药明康德', nameEn: 'WuXi AppTec', pinyin: 'ymkd', market: 'CN' },
    { ticker: '688981.SS', nameCn: '中芯国际', nameEn: 'SMIC', pinyin: 'zxgj', market: 'CN' },
    { ticker: '601899.SS', nameCn: '紫金矿业', nameEn: 'Zijin Mining', pinyin: 'zjky', market: 'CN' },
];

// All stocks combined
export const ALL_STOCKS: StockInfo[] = [...US_STOCKS, ...HK_STOCKS, ...CN_STOCKS];

/**
 * Normalize user input ticker to standard format for API calls
 * Handles:
 * - HK stocks: 700, 0700, 00700 -> 0700.HK (Yahoo Finance 4-digit format)
 * - A-shares: 600519 -> 600519.SS, 000001 -> 000001.SZ
 * - US stocks: AAPL -> AAPL (unchanged)
 */
export function normalizeTickerForApi(ticker: string): string {
    const t = ticker.trim().toUpperCase();

    // Handle existing suffix - need to normalize HK stocks
    if (t.includes('.')) {
        // HK stocks: pad to 4 digits (Yahoo Finance needs 0179.HK not 179.HK)
        if (t.endsWith('.HK')) {
            const base = t.slice(0, -3); // Remove .HK
            if (/^\d+$/.test(base)) {
                const stripped = base.replace(/^0+/, '') || '0';
                const padded = stripped.padStart(4, '0');
                return `${padded}.HK`;
            }
        }
        // A-shares and US stocks: return as-is
        return t;
    }

    // Pure numeric - determine market
    if (/^\d+$/.test(t)) {
        const stripped = t.replace(/^0+/, '') || '0';
        const padded6 = t.padStart(6, '0');

        // 6-digit codes: check A-share patterns
        if (t.length === 6) {
            const prefix = t.slice(0, 2);
            if (['60', '68'].includes(prefix)) {
                return `${t}.SS`; // Shanghai
            }
            if (['00', '30'].includes(prefix)) {
                return `${t}.SZ`; // Shenzhen
            }
        }

        // If padded to 6 digits matches A-share pattern
        if (t.length < 6) {
            const prefix6 = padded6.slice(0, 2);
            if (['60', '68'].includes(prefix6)) {
                return `${padded6}.SS`;
            }
            if (['00', '30'].includes(prefix6)) {
                return `${padded6}.SZ`;
            }
        }

        // 1-5 digit numbers (after stripping zeros): assume HK stock
        // Yahoo Finance uses 4-digit padded format (e.g., 0700.HK, 0179.HK)
        if (stripped.length >= 1 && stripped.length <= 5) {
            const padded = stripped.padStart(4, '0');
            return `${padded}.HK`;
        }
    }

    // Default: return as US stock (no suffix)
    return t;
}

/**
 * Normalize ticker for matching
 * Handles HK stock codes with leading zeros (e.g., 700, 0700, 00700 all match 0700.HK)
 */
function normalizeTickerForMatch(ticker: string): string[] {
    const t = ticker.toUpperCase().trim();
    const variants: string[] = [t];

    // If it's a HK stock ticker
    if (t.endsWith('.HK')) {
        const base = t.replace('.HK', '');
        if (/^\d+$/.test(base)) {
            // Add stripped version without leading zeros
            const stripped = base.replace(/^0+/, '') || '0';
            variants.push(stripped);
            // Add padded versions
            variants.push(stripped.padStart(4, '0'));
            variants.push(stripped.padStart(5, '0'));
        }
    }

    return variants;
}

/**
 * Normalize query for matching HK stocks
 * User input: 700, 0700, 00700 -> all should match 0700.HK
 */
function normalizeQueryVariants(query: string): string[] {
    const q = query.toUpperCase().trim();
    const variants: string[] = [q];

    // If query is purely numeric, generate HK-style variants
    if (/^\d+$/.test(q)) {
        const stripped = q.replace(/^0+/, '') || '0';
        // Try different padding levels for HK stocks
        variants.push(stripped);
        variants.push(stripped.padStart(4, '0'));
        variants.push(stripped.padStart(5, '0'));
        // Also add .HK suffix variants
        variants.push(`${stripped}.HK`);
        variants.push(`${stripped.padStart(4, '0')}.HK`);
    }

    return [...new Set(variants)]; // Remove duplicates
}

/**
 * Search stocks by query (supports ticker, Chinese name, English name, pinyin)
 * Enhanced to handle HK stock codes with varying leading zeros
 */
export function searchStocks(query: string, limit: number = 10): StockInfo[] {
    if (!query || query.trim().length === 0) {
        return [];
    }

    const q = query.toLowerCase().trim();
    const queryVariants = normalizeQueryVariants(query);

    // Score each stock based on match quality
    const scored = ALL_STOCKS.map(stock => {
        let score = 0;
        const nameCnLower = stock.nameCn.toLowerCase();
        const nameEnLower = stock.nameEn.toLowerCase();
        const pinyinLower = stock.pinyin.toLowerCase();

        // Get all ticker variants for matching (handles HK leading zeros)
        const tickerVariants = normalizeTickerForMatch(stock.ticker).map(t => t.toLowerCase());

        // Check ticker matches (including variants)
        for (const qv of queryVariants.map(v => v.toLowerCase())) {
            for (const tv of tickerVariants) {
                // Exact ticker match (highest priority)
                if (tv === qv) {
                    score = Math.max(score, 100);
                }
                // Ticker starts with query
                else if (tv.startsWith(qv)) {
                    score = Math.max(score, 90);
                }
                // Query starts with ticker base (e.g., "700" matches "0700.HK")
                else if (qv.startsWith(tv.replace('.hk', ''))) {
                    score = Math.max(score, 88);
                }
                // Ticker contains query
                else if (tv.includes(qv)) {
                    score = Math.max(score, 70);
                }
            }
        }

        // Chinese name exact match
        if (nameCnLower === q) {
            score = Math.max(score, 85);
        }
        // Chinese name contains query
        else if (nameCnLower.includes(q)) {
            score = Math.max(score, 65);
        }

        // Pinyin exact match
        if (pinyinLower === q) {
            score = Math.max(score, 80);
        }
        // Pinyin starts with query
        else if (pinyinLower.startsWith(q)) {
            score = Math.max(score, 75);
        }
        // Pinyin contains query
        else if (pinyinLower.includes(q)) {
            score = Math.max(score, 55);
        }

        // English name contains query
        if (nameEnLower.includes(q)) {
            score = Math.max(score, 50);
        }

        return { stock, score };
    });

    // Filter and sort by score
    return scored
        .filter(item => item.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, limit)
        .map(item => item.stock);
}
