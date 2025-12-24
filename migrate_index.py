#!/usr/bin/env python3
"""
自动迁移 index.html 到新设计系统
"""

import re
from pathlib import Path

def extract_body_content(html_content):
    """提取 body 标签内的主要内容"""
    # 找到 body 开始和结束标签
    body_start = html_content.find('<body')
    body_end = html_content.rfind('</body>')
    
    if body_start == -1 or body_end == -1:
        return ""
    
    # 提取 body 内容（从 > 到 </body>）
    body_start = html_content.find('>', body_start) + 1
    body_content = html_content[body_start:body_end]
    
    # 移除顶部导航栏（已在 base.html 中）
    body_content = re.sub(r'<nav\s+class="navbar.*?</nav>', '', body_content, flags=re.DOTALL)
    
    # 移除登录/注册模态框（已在 base.html 中）
    body_content = re.sub(r'<!--\s*登录模态框.*?<!--\s*注册模态框.*?</div>', '', body_content, flags=re.DOTALL)
    
    return body_content.strip()

def extract_javascript(html_content):
    """提取 JavaScript 代码"""
    scripts = []
    
    # 查找所有 <script> 标签
    pattern = r'<script[^>]*>(.*?)</script>'
    matches = re.finditer(pattern, html_content, re.DOTALL)
    
    for match in matches:
        script_content = match.group(1).strip()
        # 跳过外部脚本引用
        if not script_content or 'src=' in match.group(0):
            continue
        scripts.append(script_content)
    
    return '\n\n'.join(scripts)

def extract_styles(html_content):
    """提取自定义样式"""
    styles = []
    
    # 查找所有 <style> 标签
    pattern = r'<style[^>]*>(.*?)</style>'
    matches = re.finditer(pattern, html_content, re.DOTALL)
    
    for match in matches:
        style_content = match.group(1).strip()
        if style_content:
            styles.append(style_content)
    
    return '\n\n'.join(styles)

def generate_new_template(body_content, styles, scripts):
    """生成新的模板文件"""
    template = '''{% extends "base.html" %}

{% block title %}股票分析 - AlphaG{% endblock %}

{% block extra_css %}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

<style>
''' + styles + '''
</style>
{% endblock %}

{% block content %}
<div class="container-main py-4 animate-in fade-in">
''' + body_content + '''
</div>
{% endblock %}

{% block extra_js %}
<script>
''' + scripts + '''
</script>
{% endblock %}
'''
    return template

def main():
    # 读取原文件
    index_path = Path('templates/index.html')
    backup_path = Path('templates/index_backup.html')
    new_path = Path('templates/index_new.html')
    
    print("📖 读取原文件...")
    with open(backup_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    print("🔍 提取内容...")
    body_content = extract_body_content(original_content)
    styles = extract_styles(original_content)
    scripts = extract_javascript(original_content)
    
    print("🔧 生成新模板...")
    new_template = generate_new_template(body_content, styles, scripts)
    
    print("💾 保存新文件...")
    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(new_template)
    
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 自动迁移完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

生成的文件: templates/index_new.html

📊 提取统计:
  - Body 内容: {len(body_content)} 字符
  - CSS 样式: {len(styles)} 字符
  - JavaScript: {len(scripts)} 字符

⚠️  请手动检查以下内容:
  1. 导航栏是否被正确移除
  2. 登录/注册模态框是否被移除
  3. JavaScript 功能是否完整
  4. CSS 样式是否需要调整

🔄 下一步:
  1. 检查 index_new.html
  2. 如果满意，替换原文件: mv templates/index_new.html templates/index.html
  3. 重启服务器测试
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

if __name__ == '__main__':
    main()

