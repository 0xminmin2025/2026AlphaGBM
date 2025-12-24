# 🎨 设计系统迁移指南

## 已完成的工作

### 1. ✅ 创建设计系统核心文件

**文件**: `static/css/design-system.css`

**包含内容**:
- Nexus AI 颜色系统（深色金融终端主题）
- 统一的组件样式（卡片、按钮、输入框、表格等）
- 间距和布局系统
- 动画效果
- 响应式断点
- 滚动条样式

**核心特性**:
- CSS 变量系统，便于主题定制
- 金融专用色（红跌绿涨）
- 专业的数据可视化配色
- 完整的工具类

### 2. ✅ 创建统一页面框架

**文件**: `templates/base.html`

**包含内容**:
- 顶部固定导航栏
- 模块导航系统（股票分析、期权研究、智能体、研究笔记）
- 用户信息区（显示查询次数）
- 响应式布局
- 页脚

**特点**:
- 为未来模块预留导航位置
- "敬请期待"标签标记未开发模块
- 自动显示查询额度
- 统一的退出登录功能

### 3. ✅ 备份原有文件

**文件**: `templates/index_backup.html`

原有的 `index.html` 已备份，可随时恢复。

---

## 下一步工作

### 重构 `templates/index.html`

#### 方案 A：手动重构（推荐）

**工作量**: 2-3 小时
**优点**: 完全控制，优化代码结构
**步骤**:

1. **修改文件头部**
   ```html
   {% extends "base.html" %}
   
   {% block title %}股票分析 - AlphaG{% endblock %}
   
   {% block extra_css %}
   <!-- 页面特定样式 -->
   <style>
   ...
   </style>
   {% endblock %}
   ```

2. **移动内容区**
   ```html
   {% block content %}
   <div class="container-main py-4">
       <!-- 原有的查询表单和结果展示 -->
   </div>
   {% endblock %}
   ```

3. **更新脚本**
   ```html
   {% block extra_js %}
   <script>
   // 原有的 JavaScript 代码
   </script>
   {% endblock %}
   ```

4. **移除重复内容**
   - 删除 `<html>`, `<head>`, `<body>` 标签
   - 删除重复的导航栏代码
   - 删除登录模态框（base.html 会处理）
   - 删除重复的 CSS（由 design-system.css 提供）

5. **更新样式类名**
   - 使用设计系统的类名
   - 例如: `.text-bull`, `.text-bear`, `.card`, `.btn-primary` 等

#### 方案 B：自动化脚本（快速但可能需要调整）

创建一个 Python 脚本自动提取和转换：

```python
# 提取 <body> 中的主要内容
# 保留 JavaScript 逻辑
# 生成新的模板文件
```

---

## 设计系统使用指南

### 颜色

```html
<!-- 文本颜色 -->
<span class="text-bull">上涨 +2.5%</span>
<span class="text-bear">下跌 -1.3%</span>
<span class="text-muted">次要文本</span>

<!-- 徽章 -->
<span class="badge badge-bull">强力买入</span>
<span class="badge badge-bear">避免</span>
```

### 按钮

```html
<button class="btn btn-primary">主要按钮</button>
<button class="btn btn-secondary">次要按钮</button>
<button class="btn btn-outline">轮廓按钮</button>
<button class="btn btn-ghost">幽灵按钮</button>
```

### 卡片

```html
<div class="card shadow-lg">
    <div class="card-header">
        <h5 class="card-title">标题</h5>
    </div>
    <div class="card-body">
        内容区域
    </div>
</div>
```

### 输入框

```html
<input type="text" class="form-control" placeholder="输入股票代码">
<select class="form-select">
    <option>选项1</option>
</select>
```

### 间距

```html
<div class="spacing-4">16px 间距</div>
<div class="spacing-8">32px 间距</div>
```

### 阴影

```html
<div class="shadow">标准阴影</div>
<div class="shadow-lg">大阴影</div>
```

### 圆角

```html
<div class="rounded-lg">8px 圆角</div>
<div class="rounded-xl">12px 圆角</div>
```

---

## 快速测试

1. **启动服务器**
   ```bash
   python app.py
   ```

2. **访问** http://localhost:5002

3. **检查**
   - 导航栏是否正常显示
   - 颜色主题是否应用
   - 响应式布局是否工作
   - 动画效果是否流畅

---

## 调试技巧

### CSS 变量查看

在浏览器开发者工具中：
```javascript
// 查看所有 CSS 变量
getComputedStyle(document.documentElement).getPropertyValue('--background')
```

### 覆盖样式

如果需要临时覆盖：
```html
<style>
:root {
    --bull: hsl(142, 76%, 36%); /* 自定义绿色 */
}
</style>
```

---

## 后续优化

### 性能优化
- [ ] CSS 压缩
- [ ] 图标字体改为 SVG
- [ ] 按需加载 JavaScript

### 功能增强
- [ ] 深色/浅色主题切换
- [ ] 自定义配色方案
- [ ] 打印样式优化
- [ ] 键盘快捷键

### 新模块准备
- [ ] 期权研究页面模板
- [ ] 智能体页面模板
- [ ] 研究笔记页面模板

---

## 参考资料

- [Nexus AI UI 设计系统](设计系统文档链接)
- [shadcn/ui](https://ui.shadcn.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Bootstrap 5](https://getbootstrap.com/)

---

**版本**: 1.0.0  
**创建日期**: 2025-12-24  
**维护者**: AlphaG Team
