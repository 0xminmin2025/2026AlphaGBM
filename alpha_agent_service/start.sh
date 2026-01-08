#!/bin/bash
# AlphaGBM 智能体服务启动脚本

echo "🚀 启动 AlphaGBM 智能体服务..."

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件"
    echo "📝 请复制 env_template.txt 为 .env 并填写配置"
    echo "   cp env_template.txt .env"
    exit 1
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装Python"
    exit 1
fi

# 检查依赖
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖包..."
pip install -r requirements.txt

# 安装Playwright（如果需要）
if ! command -v playwright &> /dev/null; then
    echo "📥 安装Playwright..."
    playwright install
fi

# 启动服务
echo "✅ 启动服务..."
python3 main.py
