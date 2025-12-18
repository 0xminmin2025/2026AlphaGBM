// 反馈功能 JavaScript
// 自动添加到页面中的反馈按钮和模态框

// 当页面加载完成后执行
window.addEventListener('DOMContentLoaded', function () {
    // 创建反馈按钮并添加到页面右下角
    createFeedbackButton();
});

// 创建浮动反馈按钮
function createFeedbackButton() {
    const feedbackButton = document.createElement('button');
    feedbackButton.id = 'feedbackButton';
    feedbackButton.className = 'btn btn-primary';
    feedbackButton.innerText = '反馈建议';
    feedbackButton.style.position = 'fixed';
    feedbackButton.style.bottom = '30px';
    feedbackButton.style.right = '30px';
    feedbackButton.style.zIndex = '999';
    feedbackButton.style.borderRadius = '50px';
    feedbackButton.style.boxShadow = '0 4px 12px rgba(59, 130, 246, 0.4)';
    feedbackButton.style.transition = 'all 0.3s ease';
    feedbackButton.style.padding = '12px 20px';

    // 添加悬停效果
    feedbackButton.addEventListener('mouseenter', function () {
        this.style.transform = 'scale(1.05)';
        this.style.boxShadow = '0 6px 16px rgba(59, 130, 246, 0.5)';
    });

    feedbackButton.addEventListener('mouseleave', function () {
        this.style.transform = 'scale(1)';
        this.style.boxShadow = '0 4px 12px rgba(59, 130, 246, 0.4)';
    });

    // 绑定点击事件
    feedbackButton.addEventListener('click', openFeedbackModal);

    // 添加到页面
    document.body.appendChild(feedbackButton);
}

// 创建并显示反馈模态框
function createFeedbackModal() {
    // 检查是否已经存在模态框
    let modal = document.getElementById('feedbackModal');
    if (modal) {
        return modal;
    }

    // 创建模态框容器
    modal = document.createElement('div');
    modal.id = 'feedbackModal';
    modal.className = 'modal';

    // 添加样式
    modal.style.display = 'none';
    modal.style.position = 'fixed';
    modal.style.zIndex = '1000';
    modal.style.left = '0';
    modal.style.top = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.overflow = 'auto';
    modal.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';

    // 创建模态框内容
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    modalContent.style.backgroundColor = '#1e293b';
    modalContent.style.margin = '15% auto';
    modalContent.style.padding = '20px';
    modalContent.style.border = '1px solid #334155';
    modalContent.style.width = '90%';
    modalContent.style.maxWidth = '500px';
    modalContent.style.borderRadius = '8px';

    // 创建模态框头部
    const modalHeader = document.createElement('div');
    modalHeader.className = 'modal-header';
    modalHeader.style.display = 'flex';
    modalHeader.style.justifyContent = 'space-between';
    modalHeader.style.alignItems = 'center';
    modalHeader.style.marginBottom = '20px';

    // 创建标题
    const modalTitle = document.createElement('h2');
    modalTitle.innerText = '反馈建议';
    modalTitle.style.margin = '0';

    // 创建关闭按钮
    const closeButton = document.createElement('span');
    closeButton.className = 'close';
    closeButton.innerHTML = '&times;';
    closeButton.style.color = '#aaa';
    closeButton.style.fontSize = '28px';
    closeButton.style.fontWeight = 'bold';
    closeButton.style.cursor = 'pointer';
    closeButton.addEventListener('click', closeFeedbackModal);

    // 添加标题和关闭按钮到头部
    modalHeader.appendChild(modalTitle);
    modalHeader.appendChild(closeButton);

    // 创建模态框主体
    const modalBody = document.createElement('div');
    modalBody.className = 'modal-body';

    // 创建表单
    const feedbackForm = document.createElement('form');
    feedbackForm.id = 'feedbackForm';

    // 创建隐藏的股票代码输入框
    const tickerInput = document.createElement('input');
    tickerInput.type = 'hidden';
    tickerInput.id = 'feedbackTicker';

    // 创建反馈类型选择
    const typeGroup = createFormGroup('feedbackType', '反馈类型', 'select');
    const typeSelect = typeGroup.querySelector('select');
    const options = [
        { value: 'bug', text: '功能问题/错误' },
        { value: 'suggestion', text: '功能建议' },
        { value: 'performance', text: '性能优化' },
        { value: 'other', text: '其他反馈' }
    ];

    options.forEach(option => {
        const opt = document.createElement('option');
        opt.value = option.value;
        opt.innerText = option.text;
        typeSelect.appendChild(opt);
    });

    // 创建反馈内容输入框
    const contentGroup = createFormGroup('feedbackContent', '反馈内容', 'textarea');
    const contentTextarea = contentGroup.querySelector('textarea');
    contentTextarea.rows = '4';
    contentTextarea.placeholder = '请详细描述您的问题或建议...';

    // 创建按钮组
    const buttonGroup = document.createElement('div');
    buttonGroup.className = 'form-group';
    buttonGroup.style.display = 'flex';
    buttonGroup.style.justifyContent = 'flex-end';
    buttonGroup.style.gap = '10px';

    // 创建取消按钮
    const cancelButton = document.createElement('button');
    cancelButton.type = 'button';
    cancelButton.className = 'btn btn-secondary';
    cancelButton.innerText = '取消';
    cancelButton.addEventListener('click', closeFeedbackModal);

    // 创建提交按钮
    const submitButton = document.createElement('button');
    submitButton.type = 'button';
    submitButton.className = 'btn btn-primary';
    submitButton.innerText = '提交反馈';
    submitButton.addEventListener('click', submitFeedback);

    // 添加按钮到按钮组
    buttonGroup.appendChild(cancelButton);
    buttonGroup.appendChild(submitButton);

    // 创建消息显示区域
    const messageDiv = document.createElement('div');
    messageDiv.id = 'feedbackMessage';
    messageDiv.className = 'message';
    messageDiv.style.marginTop = '10px';
    messageDiv.style.padding = '10px';
    messageDiv.style.borderRadius = '4px';
    messageDiv.style.display = 'none';

    // 添加所有元素到表单
    feedbackForm.appendChild(tickerInput);
    feedbackForm.appendChild(typeGroup);
    feedbackForm.appendChild(contentGroup);
    feedbackForm.appendChild(buttonGroup);
    feedbackForm.appendChild(messageDiv);

    // 添加表单到模态框主体
    modalBody.appendChild(feedbackForm);

    // 添加头部和主体到模态框内容
    modalContent.appendChild(modalHeader);
    modalContent.appendChild(modalBody);

    // 添加模态框内容到模态框
    modal.appendChild(modalContent);

    // 添加模态框到页面
    document.body.appendChild(modal);

    return modal;
}

// 创建表单组辅助函数
function createFormGroup(id, labelText, type) {
    const group = document.createElement('div');
    group.className = 'form-group';
    group.style.marginBottom = '15px';

    const label = document.createElement('label');
    label.htmlFor = id;
    label.innerText = labelText;
    label.style.display = 'block';
    label.style.marginBottom = '5px';

    let input;
    if (type === 'textarea') {
        input = document.createElement('textarea');
    } else if (type === 'select') {
        input = document.createElement('select');
    } else {
        input = document.createElement('input');
        input.type = type;
    }

    input.id = id;
    input.className = 'form-control';
    input.style.width = '100%';
    input.style.padding = '8px 12px';
    input.style.borderRadius = '4px';
    input.style.border = '1px solid #334155';
    input.style.backgroundColor = '#0f172a';
    input.style.color = 'white';

    // 添加焦点样式
    input.addEventListener('focus', function () {
        this.style.borderColor = '#3b82f6';
        this.style.boxShadow = '0 0 0 0.25rem rgba(59, 130, 246, 0.25)';
        this.style.outline = 'none';
    });

    input.addEventListener('blur', function () {
        this.style.boxShadow = 'none';
    });

    group.appendChild(label);
    group.appendChild(input);

    return group;
}

// 打开反馈模态框
function openFeedbackModal() {
    // 确保模态框已创建
    let modal = document.getElementById('feedbackModal');
    if (!modal) {
        modal = createFeedbackModal();
    }

    // 尝试获取当前股票代码（如果有）
    const tickerInput = document.getElementById('tickerInput');
    if (tickerInput && tickerInput.value.trim() !== '') {
        document.getElementById('feedbackTicker').value = tickerInput.value.trim();
    }

    // 重置表单
    document.getElementById('feedbackForm').reset();
    document.getElementById('feedbackMessage').style.display = 'none';

    // 显示模态框
    modal.style.display = 'block';

    // 点击模态框外部关闭
    window.addEventListener('click', function (event) {
        if (event.target === modal) {
            closeFeedbackModal();
        }
    });

    // 按ESC键关闭
    window.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeFeedbackModal();
        }
    });
}

// 关闭反馈模态框
function closeFeedbackModal() {
    const modal = document.getElementById('feedbackModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 提交反馈
function submitFeedback() {
    // 检查用户是否已登录
    const token = localStorage.getItem('token');
    if (!token) {
        showMessage('feedbackMessage', '请先登录后再提交反馈', 'error');
        return;
    }

    // 获取表单数据
    const feedbackType = document.getElementById('feedbackType').value;
    const feedbackContent = document.getElementById('feedbackContent').value.trim();
    const feedbackTicker = document.getElementById('feedbackTicker').value;

    // 获取提交按钮
    const submitBtn = document.querySelector('#feedbackModal button.btn-primary:last-child');
    const originalText = submitBtn.innerHTML;

    // 验证表单
    if (!feedbackContent) {
        showMessage('feedbackMessage', '请填写反馈内容', 'error');
        return;
    }

    // 准备提交数据
    const feedbackData = {
        type: feedbackType,
        content: feedbackContent,
        ticker: feedbackTicker
    };

    // 显示加载状态
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 提交中...';

    // 发送请求
    fetch('/api/feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(feedbackData)
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage('feedbackMessage', '反馈提交成功，感谢您的宝贵意见！', 'success');
                // 重置表单但不关闭模态框，让用户可以看到成功消息
                setTimeout(() => {
                    closeFeedbackModal();
                }, 2000);
            } else {
                if (data.error && data.error.includes('登录')) {
                    // 登录相关错误，清除token
                    localStorage.removeItem('token');
                }
                showMessage('feedbackMessage', data.error || '提交失败，请稍后重试', 'error');
            }
        })
        .catch(error => {
            console.error('提交反馈时出错:', error);
            showMessage('feedbackMessage', '网络错误，请稍后重试', 'error');
        })
        .finally(() => {
            // 恢复按钮状态
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        });
}

// 可选的辅助函数：设置当前股票代码
function setCurrentTicker(ticker) {
    const feedbackTicker = document.getElementById('feedbackTicker');
    if (feedbackTicker) {
        feedbackTicker.value = ticker;
    }
}