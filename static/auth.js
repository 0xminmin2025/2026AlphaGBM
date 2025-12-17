/*
 * @Author: ming.chen@tsaftech.com
 * @Date: 2025-12-15 12:05:06
 * @LastEditors: ming.chen@tsaftech.com
 * @LastEditTime: 2025-12-15 15:27:34
 * Copyright (c) 2025 by Chen Ming, All Rights Reserved. 
 */
// auth.js - 用户认证相关功能

// 模态框控制函数
function showLoginModal() {
    document.getElementById('loginModal').style.display = 'block';
    document.body.style.overflow = 'hidden'; // 阻止背景滚动
}

function showRegisterModal() {
    document.getElementById('registerModal').style.display = 'block';
    document.body.style.overflow = 'hidden'; // 阻止背景滚动
}

function hideModals() {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('registerModal').style.display = 'none';
    document.body.style.overflow = 'auto'; // 恢复背景滚动
}

// 页面加载时执行的认证初始化
function initAuth() {
    // 检查登录状态
    if (typeof checkLoginStatus === 'function') {
        checkLoginStatus();
    }

    // 为关闭按钮添加点击事件
    const closeButtons = document.querySelectorAll('.close');
    closeButtons.forEach(button => {
        button.addEventListener('click', hideModals);
    });

    // 点击模态框外部关闭
    window.addEventListener('click', function (event) {
        if (event.target === document.getElementById('loginModal') ||
            event.target === document.getElementById('registerModal')) {
            hideModals();
        }
    });

    // 添加移动端菜单按钮
    if (0 && !document.getElementById('mobileAuthButtons')) {
        const authContainer = document.createElement('div');
        authContainer.className = 'md:hidden mt-2';
        authContainer.id = 'mobileAuthButtons';
        authContainer.innerHTML = `
            <button id="mobileLoginBtn" class="btn btn-sm btn-primary me-2" onclick="showLoginModal()">登录</button>
            <button id="mobileRegisterBtn" class="btn btn-sm btn-secondary" onclick="showRegisterModal()">注册</button>
            <div id="mobileUserInfo" class="hidden mt-2">
                <span id="mobileUsernameDisplay" class="text-white mr-2">用户: </span>
                <button id="mobileLogoutBtn" class="btn btn-sm btn-secondary" onclick="handleLogout()">退出登录</button>
            </div>
        `;

        const parent = document.querySelector('.row.mb-4.align-items-center');
        if (parent) {
            parent.appendChild(authContainer);
        } else {
            // 如果找不到特定容器，添加到body
            document.body.appendChild(authContainer);
        }
    }
}

// 页面加载完成后初始化认证功能
document.addEventListener('DOMContentLoaded', initAuth);
