/* ==========================================
   G8BikeShare - 全站通用 JavaScript (main.js)
   負責：頭像選單、登入狀態同步、全站天氣小工具
   ========================================== */

document.addEventListener("DOMContentLoaded", () => {
    // 取得導覽列元素
    const navAvatarBtn = document.getElementById("navAvatarBtn");
    const navAvatarMenu = document.getElementById("navAvatarMenu");
    const navSignInLink = document.getElementById("navSignInLink");
    const navAvatarUsername = document.getElementById("navAvatarUsername");
    const navAvatarSubtext = document.getElementById("navAvatarSubtext");
    const navLogoutBtn = document.getElementById("navLogoutBtn");
    const navToggleBtn = document.getElementById("navToggleBtn");
    const mobileNavMenu = document.getElementById("mobileNavMenu");


    function closeAvatarMenu() {
        if (navAvatarMenu) navAvatarMenu.classList.remove("open");
        if (navAvatarBtn) navAvatarBtn.setAttribute("aria-expanded", "false");
    }
    
    function closeMobileMenu() {
        if (mobileNavMenu) {
            mobileNavMenu.classList.remove("open");
            mobileNavMenu.hidden = true;
        }
        if (navToggleBtn) {
            navToggleBtn.classList.remove("open");
            navToggleBtn.setAttribute("aria-expanded", "false");
        }
    }
    
    // --- 1. 頭像選單開關邏輯 ---
    if (navAvatarBtn && navAvatarMenu) {
        navAvatarBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const isOpen = navAvatarMenu.classList.toggle("open");
            navAvatarBtn.setAttribute("aria-expanded", isOpen);
        });
    }

    // --- 1.1 手機導覽選單開關 ---
    if (navToggleBtn && mobileNavMenu) {
        navToggleBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const willOpen = mobileNavMenu.hidden || !mobileNavMenu.classList.contains("open");

            if (willOpen) {
                mobileNavMenu.hidden = false;
                mobileNavMenu.classList.add("open");
                navToggleBtn.classList.add("open");
                navToggleBtn.setAttribute("aria-expanded", "true");
            } else {
                closeMobileMenu();
            }
        });
        
        mobileNavMenu.addEventListener("click", (e) => {
            e.stopPropagation();
        });

        window.addEventListener("resize", () => {
            if (window.innerWidth > 720) {
                closeMobileMenu();
            }
        });
    }

    // 點擊選單以外的地方自動關閉
    document.addEventListener("click", (e) => {
        if (navAvatarMenu && navAvatarBtn) {
            if (!navAvatarMenu.contains(e.target) && !navAvatarBtn.contains(e.target)) {
                closeAvatarMenu();
            }
        }

        if (mobileNavMenu && navToggleBtn) {
            if (!mobileNavMenu.contains(e.target) && !navToggleBtn.contains(e.target)) {
                closeMobileMenu();
            }
        }
    });

    // --- 2. 登入狀態檢查 (向後端 API 確認) ---
    async function checkLoginStatus() {
        try {
            const response = await fetch("/api/auth/me");
            const result = await response.json();

            if (result.authenticated && result.user) {
                // 已登入狀態：隱藏 Sign In 連結，更新頭像資訊
                if (navSignInLink) navSignInLink.classList.add("hidden");
                if (navAvatarUsername) navAvatarUsername.textContent = result.user.username;
                if (navAvatarSubtext) navAvatarSubtext.textContent = "Signed in";
                if (navLogoutBtn) navLogoutBtn.classList.remove("hidden");
            } else {
                // 未登入狀態：顯示 Sign In 連結
                if (navSignInLink) navSignInLink.classList.remove("hidden");
                if (navLogoutBtn) navLogoutBtn.classList.add("hidden");
            }
        } catch (error) {
            console.log("Session Check Error:", error);
        }
    }

    // --- 3. 登出功能 ---
    if (navLogoutBtn) {
        navLogoutBtn.addEventListener("click", async () => {
            try {
                await fetch("/api/auth/logout", { method: "POST" });
                window.location.href = "/"; // 登出後回首頁
            } catch (error) {
                alert("Logout failed");
            }
        });
    }

    // 執行檢查
    checkLoginStatus();
});