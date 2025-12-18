// 确保hideModals函数可用
function ensureHideModals() {
    if (typeof hideModals === 'function') {
        hideModals();
    } else {
        // 如果外部未定义，则使用内部实现
        const loginModal = document.getElementById('loginModal');
        const registerModal = document.getElementById('registerModal');
        if (loginModal) loginModal.style.display = 'none';
        if (registerModal) registerModal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// 邮箱验证函数
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// 密码验证函数
function validatePassword(password) {
    return password.length >= 6; // 密码至少6位
}

// 用户名验证函数
function validateUsername(username) {
    return username.length >= 2; // 用户名至少2位
}

// 验证码验证函数
function validateCode(code) {
    return code.length === 6 && /^\d+$/.test(code); // 6位数字
}

// 显示消息函数
function showMessage(elementId, message, isError = false) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.style.color = isError ? '#ef4444' : '#10b981';
        element.style.display = 'block';

        // 3秒后自动隐藏消息
        setTimeout(() => {
            element.style.display = 'none';
        }, 6000);
    }
}

// 倒计时函数
function startCountdown(buttonId, seconds = 300) {
    const button = document.getElementById(buttonId);
    if (!button) return;

    let count = seconds;
    button.disabled = true;
    button.textContent = `${count}秒后重试`;

    const interval = setInterval(() => {
        count--;
        if (count <= 0) {
            clearInterval(interval);
            button.disabled = false;
            button.textContent = '获取验证码';
        } else {
            button.textContent = `${count}秒后重试`;
        }
    }, 1000);
}

// 请求验证码函数
async function requestVerificationCode() {
    const email = document.getElementById('registerEmail').value;

    if (!validateEmail(email)) {
        showMessage('registerMessage', '请输入有效的邮箱地址', true);
        return;
    }

    try {
        const response = await fetch('/api/register/request-code', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('registerMessage', '验证码已发送到您的邮箱');
            startCountdown('sendCodeBtn');
        } else {
            showMessage('registerMessage', data.error || '发送验证码失败', true);
        }
    } catch (error) {
        console.error('请求验证码出错:', error);
        showMessage('registerMessage', '网络错误，请稍后重试', true);
    }
}

// 处理注册函数（简化版，无需验证码）
async function handleRegister() {
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;

    // 表单验证
    if (!validateUsername(username)) {
        showMessage('registerMessage', '用户名至少2个字符', true);
        return;
    }

    if (!validateEmail(email)) {
        showMessage('registerMessage', '请输入有效的邮箱地址', true);
        return;
    }

    if (!validatePassword(password)) {
        showMessage('registerMessage', '密码至少6个字符', true);
        return;
    }

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showMessage('registerMessage', '注册成功！');
            // 保存token和用户信息到localStorage
            const user = data.username || username;
            const token = data.access_token || data.token; // 兼容access_token和token字段
            localStorage.setItem('token', token);
            localStorage.setItem('username', user);
            console.log('注册成功，保存用户信息:', user);

            setTimeout(() => {
                // 隐藏所有模态框
                ensureHideModals();
                // 检查登录状态
                checkLoginStatus();
            }, 1000);
        } else {
            showMessage('registerMessage', data.error || '注册失败', true);
        }
    } catch (error) {
        console.error('注册请求出错:', error);
        showMessage('registerMessage', '网络错误，请稍后重试', true);
    }
}

// 处理登录函数
async function handleLogin() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    // 表单验证
    if (!validateEmail(email)) {
        showMessage('loginMessage', '请输入有效的邮箱地址', true);
        return;
    }

    if (!password) {
        showMessage('loginMessage', '请输入密码', true);
        return;
    }

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            showMessage('loginMessage', '登录成功！');
            // 保存token和用户信息到localStorage
            const user = data.username || data.user || data.name;
            const token = data.access_token || data.token; // 兼容access_token和token字段
            localStorage.setItem('token', token);
            localStorage.setItem('username', user);
            console.log('登录成功，保存用户信息:', user);

            setTimeout(() => {
                // 隐藏所有模态框
                ensureHideModals();
                // 检查登录状态
                checkLoginStatus();
            }, 1000);
        } else {
            showMessage('loginMessage', data && data.message ? data.message : '登录失败，请检查用户名和密码', true);
        }
    } catch (error) {
        console.error('登录请求错误:', error);
        showMessage('loginMessage', '网络请求错误，请稍后重试', true);
    }
}

// 获取查询次数信息（当前系统不限制查询次数，此函数保留但不执行任何操作）
async function fetchQueryCountInfo() {
    // 当前系统不限制查询次数，此函数为空实现
    // 如果将来需要实现查询次数限制，可以在此处添加逻辑
    return;
}

// 处理退出登录函数
function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    checkLoginStatus();
}

// 检查登录状态函数
function checkLoginStatus() {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');

    console.log('检查登录状态:', { token: !!token, username });

    // 更新桌面端显示
    const authButtons = document.getElementById('authButtons');
    const userInfo = document.getElementById('userInfo');
    const usernameDisplay = document.getElementById('usernameDisplay');
    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');

    // 更新移动端显示
    const mobileLoginBtn = document.getElementById('mobileLoginBtn');
    const mobileUserInfo = document.getElementById('mobileUserInfo');
    const mobileUsernameDisplay = document.getElementById('mobileUsernameDisplay');

    if (token && username) {
        // 已登录状态
        console.log('用户已登录，用户名:', username);

        // 桌面端处理
        if (authButtons) authButtons.style.display = 'flex';
        if (userInfo) {
            userInfo.style.display = 'flex';
            if (usernameDisplay) usernameDisplay.textContent = `用户: ${username}`;
        }
        if (loginBtn) loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'inline-block';

        // 移动端处理
        if (mobileLoginBtn) mobileLoginBtn.style.display = 'none';
        if (mobileUserInfo) {
            mobileUserInfo.style.display = 'flex';
            if (mobileUsernameDisplay) mobileUsernameDisplay.textContent = `用户: ${username}`;
        }

        // 获取并显示查询次数信息
        fetchQueryCountInfo();
    } else {
        // 未登录状态
        console.log('用户未登录');

        // 桌面端处理
        if (authButtons) authButtons.style.display = 'flex';
        if (userInfo) {
            userInfo.style.display = 'none';
            if (usernameDisplay) usernameDisplay.textContent = '';
        }
        if (loginBtn) loginBtn.style.display = 'inline-block';
        if (logoutBtn) logoutBtn.style.display = 'none';


        // 移动端处理
        if (mobileLoginBtn) mobileLoginBtn.style.display = 'block';
        if (mobileUserInfo) mobileUserInfo.style.display = 'none';
    }
}

// 获取当前用户信息
function getCurrentUser() {
    const username = localStorage.getItem('username');
    return username ? { username } : null;
}

// 检查认证状态并更新UI显示
function checkAuthStatus() {
    const token = localStorage.getItem('token');
    const user = getCurrentUser();

    // 更新UI显示的逻辑
    console.log('当前认证状态:', token ? '已登录' : '未登录');
    console.log('当前用户:', user);

    return token !== null;
}