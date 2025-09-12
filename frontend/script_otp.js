document.addEventListener('DOMContentLoaded', function () {
    const body = document.body;
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const generateBtn = document.getElementById('generate-btn');
    const otpValueDisplay = document.getElementById('otp-value');
    const totpCountdown = document.getElementById('totp-countdown');
    const qrcodeContainer = document.getElementById('qrcode');
    const uriText = document.getElementById('uri-text');
    const starsContainer = document.querySelector('.stars');
    const cloudsContainer = document.querySelector('.clouds');
    
    // === Tạo sao ===
    function createStars() {
        starsContainer.innerHTML = '';
        const numStars = 80;
        for (let i = 0; i < numStars; i++) {
            const star = document.createElement('div');
            star.classList.add('star');
            star.style.top = Math.random() * 100 + '%';
            star.style.left = Math.random() * 100 + '%';
            const size = Math.random() * 3 + 1;
            star.style.width = size + 'px';
            star.style.height = size + 'px';
            star.style.animationDuration = (Math.random() * 3 + 2) + 's';
            starsContainer.appendChild(star);
        }
    }
     // === Tạo mây ===
    function createClouds() {
        cloudsContainer.innerHTML = '';
        const numClouds = 5;
        for (let i = 0; i < numClouds; i++) {
            const cloud = document.createElement('div');
            cloud.classList.add('cloud');
            cloud.style.top = Math.random() * 60 + '%';
            cloud.style.left = '-200px';
            cloud.style.animationDuration = (Math.random() * 40 + 30) + 's';
            cloud.style.transform = `scale(${Math.random() * 0.6 + 0.8})`;
            cloudsContainer.appendChild(cloud);
        }
    }

    // === Tải theme từ localStorage ===
    const isDarkSaved = localStorage.getItem('darkMode') === 'true';
    if (isDarkSaved) {
        body.classList.add('dark-mode');
        createStars();
    } else {
        body.classList.add('light-mode');
        createClouds();
    }

// === Toggle theme khi bấm nút ===
themeToggleBtn.addEventListener('click', function () {
    const isDarkMode = body.classList.contains('dark-mode');

    if (isDarkMode) {
        body.classList.remove('dark-mode');
        body.classList.add('light-mode');
        createClouds();
    } else {
        body.classList.remove('light-mode');
        body.classList.add('dark-mode');
        createStars();
    }

    localStorage.setItem('darkMode', !isDarkMode);
});

// Tạo OTP và mã QR
    generateBtn.addEventListener('click', function() {
        const secretKey = document.getElementById('secret-key').value.trim();
        const issuer = document.getElementById('issuer').value.trim();
        const account = document.getElementById('account').value.trim();
        
        if (!secretKey) {
            alert('Please enter a secret key');
            return;
        }
        
        // Tạo OTP
        generateTOTP(secretKey);
        startTOTPCountdown();
        
        // Tạo QR code
        generateQRCode(secretKey, issuer, account);
    });
    
    // Chuyển đổi Base32 sang hex (để tạo OTP)
    function base32ToHex(base32) {
        const base32chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
        let bits = '';
        let hex = '';
        
        for (let i = 0; i < base32.length; i++) {
            const val = base32chars.indexOf(base32.charAt(i).toUpperCase());
            if (val === -1) continue; // Bỏ qua các ký tự không có trong base32
            bits += val.toString(2).padStart(5, '0');
        }
        
        // Chuyển đổi bit sang hex
        for (let i = 0; i < bits.length; i += 4) {
            const chunk = bits.substr(i, 4);
            if (chunk.length === 4) {
                hex += parseInt(chunk, 2).toString(16);
            }
        }
        
        return hex;
    }
    
    // Tạo OTP
    function generateTOTP(secret) {
        // Lấy thời gian hiện tại tính bằng giây và chia cho 30 để có bộ đếm thời gian
        const epoch = Math.floor(Date.now() / 1000);
        const timeCounter = Math.floor(epoch / 30);
        
        // Chuyển đổi bộ đếm thời gian sang hex và pad thành 16 ký tự
        const timeHex = timeCounter.toString(16).padStart(16, '0');
        
        // Convert the secret from base32 to hex
        const secretHex = base32ToHex(secret);
        
        // Tạo HMAC-SHA1
        const shaObj = new jsSHA("SHA-1", "HEX");
        shaObj.setHMACKey(secretHex, "HEX");
        shaObj.update(timeHex);
        const hmac = shaObj.getHMAC("HEX");
        
        // Lấy offset (nibly cuối cùng của hmac)
        const offset = parseInt(hmac.substring(hmac.length - 1), 16);
        
        // Lấy 4 byte bắt đầu từ vị trí offset
        const otp = (parseInt(hmac.substr(offset * 2, 8), 16) & 0x7fffffff) % 1000000;
        
        // Hiển thị OTP với số 0 đứng đầu nếu cần
        otpValueDisplay.textContent = otp.toString().padStart(6, '0');
    }
    
    // Bắt đầu bộ đếm ngược TOTP
    let countdownInterval;
    function startTOTPCountdown() {
        // Xóa bất kỳ khoảng thời gian hiện có nào
        if (countdownInterval) {
            clearInterval(countdownInterval);
        }
        
        const progressBar = document.getElementById('countdown-progress');
        
        function updateCountdown() {
            const epoch = Math.floor(Date.now() / 1000);
            const secondsRemaining = 30 - (epoch % 30);
            const progressPercentage = (secondsRemaining / 30) * 100;
            
            totpCountdown.textContent = `Code refreshes in ${secondsRemaining} seconds`;
            progressBar.style.width = `${progressPercentage}%`;
            
            // Tạo lại TOTP khi hết thời gian
            if (secondsRemaining === 30) {
                const secretKey = document.getElementById('secret-key').value.trim();
                generateTOTP(secretKey);
            }
        }
        
        // Cập nhật ngay lập tức và sau đó mỗi giây
        updateCountdown();
        countdownInterval = setInterval(updateCountdown, 1000);
    }
    
    // Tạo QR code
    function generateQRCode(secret, issuer, account) {
        // Xóa mã QR trước đó
        qrcodeContainer.innerHTML = '';
        
        // Tạo otpauth URI - format: otpauth://totp/Issuer:Account?secret=SECRET&issuer=Issuer
        const uri = `otpauth://totp/${encodeURIComponent(issuer)}:${encodeURIComponent(account)}?secret=${secret}&issuer=${encodeURIComponent(issuer)}`;
        
        // Hiển thị URI
        uriText.textContent = uri;
        
        // Tạo QR code mới
        new QRCode(qrcodeContainer, {
            text: uri,
            width: 200,
            height: 200,
            colorDark: document.body.classList.contains('dark-mode') ? "#ffffff" : "#000000",
            colorLight: document.body.classList.contains('dark-mode') ? "#1e1e1e" : "#ffffff",
        });
    }
    
    // Tạo TOTP ban đầu với các giá trị mặc định
    generateBtn.click();
});
