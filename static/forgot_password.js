// 忘记密码功能实现

// 动态创建忘记密码模态框
function createForgotPasswordModal() {
    // 创建模态框容器
    const modalContainer = document.createElement('div');
    modalContainer.id = 'forgotPasswordModal';
    modalContainer.className = 'modal';

    // 设置模态框样式
    modalContainer.style.display = 'none';
    modalContainer.style.position = 'fixed';
    modalContainer.style.zIndex = '1000';
    modalContainer.style.left = '0';
    modalContainer.style.top = '0';
    modalContainer.style.width = '100%';
    modalContainer.style.height = '100%';
    modalContainer.style.overflow = 'auto';
    modalContainer.style.backgroundColor = 'rgba(0,0,0,0.4)';

    // 创建模态框内容
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    modalContent.style.backgroundColor = '#1a1a1a';
    modalContent.style.margin = '15% auto';
    modalContent.style.padding = '20px';
    modalContent.style.border = '1px solid #333';
    modalContent.style.width = '80%';
    modalContent.style.maxWidth = '500px';
    modalContent.style.borderRadius = '8px';
    modalContent.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
    modalContent.style.color = '#e0e0e0';

    // 创建模态框头部
    const modalHeader = document.createElement('div');
    modalHeader.className = 'modal-header';
    modalHeader.style.display = 'flex';
    modalHeader.style.justifyContent = 'space-between';
    modalHeader.style.alignItems = 'center';
    modalHeader.style.marginBottom = '20px';

    const modalTitle = document.createElement('h2');
    modalTitle.textContent = '重置密码';
    modalTitle.style.margin = '0';

    const closeButton = document.createElement('span');
    closeButton.className = 'close';
    closeButton.innerHTML = '&times;';
    closeButton.style.color = '#888';
    closeButton.style.fontSize = '28px';
    closeButton.style.fontWeight = 'bold';
    closeButton.style.cursor = 'pointer';
    closeButton.addEventListener('click', hideForgotPasswordModal);

    modalHeader.appendChild(modalTitle);
    modalHeader.appendChild(closeButton);

    // 创建模态框主体
    const modalBody = document.createElement('div');
    modalBody.className = 'modal-body';

    // 创建表单
    const form = document.createElement('form');
    form.id = 'forgotPasswordForm';

    // 创建邮箱输入
    const emailGroup = document.createElement('div');
    emailGroup.className = 'form-group';
    emailGroup.style.marginBottom = '15px';

    const emailLabel = document.createElement('label');
    emailLabel.setAttribute('for', 'forgotEmail');
    emailLabel.textContent = '邮箱';
    emailLabel.style.display = 'block';
    emailLabel.style.marginBottom = '5px';

    const emailInput = document.createElement('input');
    emailInput.type = 'email';
    emailInput.id = 'forgotEmail';
    emailInput.required = true;
    emailInput.className = 'form-control';
    emailInput.style.width = '100%';
    emailInput.style.padding = '8px 12px';
    emailInput.style.border = '1px solid #444';
    emailInput.style.borderRadius = '4px';
    emailInput.style.backgroundColor = '#2a2a2a';
    emailInput.style.color = '#e0e0e0';

    emailGroup.appendChild(emailLabel);
    emailGroup.appendChild(emailInput);

    // 创建验证码输入
    const codeGroup = document.createElement('div');
    codeGroup.className = 'form-group';
    codeGroup.style.marginBottom = '15px';

    const codeLabel = document.createElement('label');
    codeLabel.setAttribute('for', 'forgotCode');
    codeLabel.textContent = '验证码';
    codeLabel.style.display = 'block';
    codeLabel.style.marginBottom = '5px';

    const codeContainer = document.createElement('div');
    codeContainer.style.display = 'flex';

    const codeInput = document.createElement('input');
    codeInput.type = 'text';
    codeInput.id = 'forgotCode';
    codeInput.required = true;
    codeInput.className = 'form-control';
    codeInput.style.flex = '1';
    codeInput.style.marginRight = '10px';
    codeInput.style.padding = '8px 12px';
    codeInput.style.border = '1px solid #444';
    codeInput.style.borderRadius = '4px';
    codeInput.style.backgroundColor = '#2a2a2a';
    codeInput.style.color = '#e0e0e0';

    const sendCodeButton = document.createElement('button');
    sendCodeButton.type = 'button';
    sendCodeButton.id = 'sendResetCodeBtn';
    sendCodeButton.className = 'btn btn-secondary';
    sendCodeButton.textContent = '获取验证码';
    sendCodeButton.style.padding = '8px 16px';
    sendCodeButton.style.backgroundColor = '#444';
    sendCodeButton.style.color = '#e0e0e0';
    sendCodeButton.style.border = 'none';
    sendCodeButton.style.borderRadius = '4px';
    sendCodeButton.style.cursor = 'pointer';
    sendCodeButton.addEventListener('click', requestPasswordResetCode);

    codeContainer.appendChild(codeInput);
    codeContainer.appendChild(sendCodeButton);
    codeGroup.appendChild(codeLabel);
    codeGroup.appendChild(codeContainer);

    // 创建新密码输入
    const passwordGroup = document.createElement('div');
    passwordGroup.className = 'form-group';
    passwordGroup.style.marginBottom = '15px';

    const passwordLabel = document.createElement('label');
    passwordLabel.setAttribute('for', 'newPassword');
    passwordLabel.textContent = '新密码';
    passwordLabel.style.display = 'block';
    passwordLabel.style.marginBottom = '5px';

    const passwordInput = document.createElement('input');
    passwordInput.type = 'password';
    passwordInput.id = 'newPassword';
    passwordInput.required = true;
    passwordInput.className = 'form-control';
    passwordInput.style.width = '100%';
    passwordInput.style.padding = '8px 12px';
    passwordInput.style.border = '1px solid #444';
    passwordInput.style.borderRadius = '4px';
    passwordInput.style.backgroundColor = '#2a2a2a';
    passwordInput.style.color = '#e0e0e0';

    passwordGroup.appendChild(passwordLabel);
    passwordGroup.appendChild(passwordInput);

    // 创建确认密码输入
    const confirmGroup = document.createElement('div');
    confirmGroup.className = 'form-group';
    confirmGroup.style.marginBottom = '15px';

    const confirmLabel = document.createElement('label');
    confirmLabel.setAttribute('for', 'confirmPassword');
    confirmLabel.textContent = '确认新密码';
    confirmLabel.style.display = 'block';
    confirmLabel.style.marginBottom = '5px';

    const confirmInput = document.createElement('input');
    confirmInput.type = 'password';
    confirmInput.id = 'confirmPassword';
    confirmInput.required = true;
    confirmInput.className = 'form-control';
    confirmInput.style.width = '100%';
    confirmInput.style.padding = '8px 12px';
    confirmInput.style.border = '1px solid #444';
    confirmInput.style.borderRadius = '4px';
    confirmInput.style.backgroundColor = '#2a2a2a';
    confirmInput.style.color = '#e0e0e0';

    confirmGroup.appendChild(confirmLabel);
    confirmGroup.appendChild(confirmInput);

    // 创建按钮组
    const buttonGroup = document.createElement('div');
    buttonGroup.className = 'form-group';
    buttonGroup.style.marginBottom = '15px';

    const resetButton = document.createElement('button');
    resetButton.type = 'button';
    resetButton.id = 'resetPasswordBtn';
    resetButton.className = 'btn btn-primary';
    resetButton.textContent = '重置密码';
    resetButton.style.padding = '8px 16px';
    resetButton.style.backgroundColor = '#0066cc';
    resetButton.style.color = 'white';
    resetButton.style.border = 'none';
    resetButton.style.borderRadius = '4px';
    resetButton.style.cursor = 'pointer';
    resetButton.style.marginRight = '10px';
    resetButton.addEventListener('click', handlePasswordReset);

    const backToLogin = document.createElement('a');
    backToLogin.href = 'javascript:void(0)';
    backToLogin.textContent = '返回登录';
    backToLogin.style.color = '#0066cc';
    backToLogin.addEventListener('click', function () {
        hideForgotPasswordModal();
        if (typeof showLoginModal === 'function') {
            showLoginModal();
        }
    });

    const span = document.createElement('span');
    span.style.marginLeft = '10px';
    span.appendChild(backToLogin);

    buttonGroup.appendChild(resetButton);
    buttonGroup.appendChild(span);

    // 创建消息显示区域
    const messageDiv = document.createElement('div');
    messageDiv.id = 'forgotPasswordMessage';
    messageDiv.className = 'message';
    messageDiv.style.minHeight = '20px';

    // 组装表单
    form.appendChild(emailGroup);
    form.appendChild(codeGroup);
    form.appendChild(passwordGroup);
    form.appendChild(confirmGroup);
    form.appendChild(buttonGroup);
    form.appendChild(messageDiv);

    modalBody.appendChild(form);

    // 组装模态框
    modalContent.appendChild(modalHeader);
    modalContent.appendChild(modalBody);
    modalContainer.appendChild(modalContent);

    // 添加到body
    document.body.appendChild(modalContainer);

    // 添加点击模态框外部关闭的事件
    modalContainer.addEventListener('click', function (event) {
        if (event.target === modalContainer) {
            hideForgotPasswordModal();
        }
    });
}

// 显示忘记密码模态框
function showForgotPasswordModal() {
    // 如果模态框不存在，则创建
    if (!document.getElementById('forgotPasswordModal')) {
        createForgotPasswordModal();
    }

    // 隐藏其他模态框
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (modal.id !== 'forgotPasswordModal') {
            modal.style.display = 'none';
        }
    });

    // 显示忘记密码模态框
    const modal = document.getElementById('forgotPasswordModal');
    modal.style.display = 'block';

    // 清空消息
    document.getElementById('forgotPasswordMessage').textContent = '';
}

// 隐藏忘记密码模态框
function hideForgotPasswordModal() {
    const modal = document.getElementById('forgotPasswordModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// 请求密码重置验证码
async function requestPasswordResetCode() {
    const email = document.getElementById('forgotEmail').value;
    const messageDiv = document.getElementById('forgotPasswordMessage');
    const button = document.getElementById('sendResetCodeBtn');

    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        messageDiv.textContent = '请输入有效的邮箱地址';
        messageDiv.style.color = '#ef4444';
        messageDiv.style.display = 'block';
        return;
    }

    try {
        // 禁用按钮，防止重复点击
        button.disabled = true;
        button.textContent = '发送中...';

        const response = await fetch('/api/forgot-password/request-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (response.ok) {
            messageDiv.textContent = '验证码已发送到您的邮箱';
            messageDiv.style.color = '#10b981';
            messageDiv.style.display = 'block';

            // 倒计时
            let countdown = 60;
            button.textContent = `${countdown}秒后重试`;

            const timer = setInterval(() => {
                countdown--;
                button.textContent = `${countdown}秒后重试`;

                if (countdown <= 0) {
                    clearInterval(timer);
                    button.disabled = false;
                    button.textContent = '获取验证码';
                }
            }, 1000);
        } else {
            messageDiv.textContent = data.error || '发送验证码失败';
            messageDiv.style.color = '#ef4444';
            messageDiv.style.display = 'block';
            button.disabled = false;
            button.textContent = '获取验证码';
        }
    } catch (error) {
        console.error('请求验证码出错:', error);
        messageDiv.textContent = '网络错误，请稍后重试';
        messageDiv.style.color = '#ef4444';
        messageDiv.style.display = 'block';
        button.disabled = false;
        button.textContent = '获取验证码';
    }
}

// 处理密码重置
async function handlePasswordReset() {
    const email = document.getElementById('forgotEmail').value;
    const code = document.getElementById('forgotCode').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const messageDiv = document.getElementById('forgotPasswordMessage');

    // 验证输入
    if (newPassword !== confirmPassword) {
        messageDiv.textContent = '两次输入的密码不一致';
        messageDiv.style.color = '#ef4444';
        messageDiv.style.display = 'block';
        return;
    }

    if (newPassword.length < 6) {
        messageDiv.textContent = '密码长度至少为6个字符';
        messageDiv.style.color = '#ef4444';
        messageDiv.style.display = 'block';
        return;
    }

    // 验证码验证
    if (code.length !== 6 || !/^\d+$/.test(code)) {
        messageDiv.textContent = '验证码必须是6位数字';
        messageDiv.style.color = '#ef4444';
        messageDiv.style.display = 'block';
        return;
    }

    try {
        const response = await fetch('/api/forgot-password/reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email,
                verification_code: code,
                new_password: newPassword
            })
        });

        const data = await response.json();

        if (response.ok) {
            messageDiv.textContent = '密码重置成功，请使用新密码登录';
            messageDiv.style.color = '#10b981';
            messageDiv.style.display = 'block';

            // 3秒后跳转回登录页面
            setTimeout(() => {
                hideForgotPasswordModal();
                if (typeof showLoginModal === 'function') {
                    showLoginModal();
                }
            }, 3000);
        } else {
            messageDiv.textContent = data.error || '密码重置失败';
            messageDiv.style.color = '#ef4444';
            messageDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('重置密码出错:', error);
        messageDiv.textContent = '网络错误，请稍后重试';
        messageDiv.style.color = '#ef4444';
        messageDiv.style.display = 'block';
    }
}

// 在登录页面添加忘记密码链接
function addForgotPasswordLink() {
    // 查找登录按钮所在的元素
    const loginButtons = document.querySelectorAll('button.btn-primary');
    let loginButton = null;

    for (let btn of loginButtons) {
        if (btn.textContent.includes('登录') &&
            btn.closest('form[id="loginForm"]')) {
            loginButton = btn;
            break;
        }
    }

    if (loginButton) {
        // 获取包含按钮的div
        const buttonContainer = loginButton.parentElement;

        // 检查是否已经有忘记密码链接
        if (!buttonContainer.querySelector('a[onclick="showForgotPasswordModal()"]')) {
            // 创建空格和链接
            const spaceSpan = document.createElement('span');
            spaceSpan.style.marginLeft = '10px';

            const forgotLink = document.createElement('a');
            forgotLink.href = 'javascript:void(0)';
            forgotLink.textContent = '忘记密码？';
            // forgotLink.style.color = '#0066cc';
            forgotLink.onclick = showForgotPasswordModal;

            spaceSpan.appendChild(forgotLink);
            buttonContainer.appendChild(spaceSpan);
        }
    }
}

// 页面加载时执行
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
        addForgotPasswordLink();
    });
} else {
    addForgotPasswordLink();
}