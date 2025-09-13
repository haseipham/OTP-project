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
    generateBtn.addEventListener('click', async function() {
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
        await generateQRCode(secretKey, issuer, account);
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
    
    // Tạo OTP using server-side core algorithm
    async function generateTOTP(secret) {
        console.log('generateTOTP called with secret:', secret);
        try {
            const response = await fetch('/api/v2/demo_totp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ secret: secret })
            });
            
            console.log('Server response status:', response.status);
            const data = await response.json();
            console.log('Server response data:', data);
            
            if (response.ok && data.otp_code) {
                // Hiển thị OTP với số 0 đứng đầu nếu cần
                otpValueDisplay.textContent = data.otp_code.toString().padStart(6, '0');
                console.log('TOTP generated via server:', data.otp_code);
            } else {
                throw new Error(data.error || 'Failed to generate TOTP');
            }
            
        } catch (error) {
            console.error('Error generating TOTP:', error);
            otpValueDisplay.textContent = 'ERROR';
        }
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
    
    // Tạo QR code using server-side generation
    async function generateQRCode(secret, issuer, account) {
        // Xóa mã QR trước đó
        qrcodeContainer.innerHTML = '';
        
        try {
            // Call server-side QR code generation
            const response = await fetch('/api/v2/demo_qr', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    secret: secret,
                    issuer: issuer,
                    account: account
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.qr_code) {
                // Display URI
                uriText.textContent = data.uri;
                
                // Create img element and set source
                const img = document.createElement('img');
                img.src = data.qr_code;
                img.style.width = '200px';
                img.style.height = '200px';
                img.alt = 'QR Code';
                
                qrcodeContainer.appendChild(img);
                
                console.log('QR code generated successfully via server');
            } else {
                throw new Error(data.error || 'Failed to generate QR code');
            }
            
        } catch (error) {
            console.error('Error generating QR code:', error);
            qrcodeContainer.innerHTML = '<p style="color: red;">Error generating QR code: ' + error.message + '</p>';
            
            // Fallback: show URI text
            const uri = `otpauth://totp/${encodeURIComponent(issuer)}:${encodeURIComponent(account)}?secret=${secret}&issuer=${encodeURIComponent(issuer)}`;
            uriText.textContent = uri;
        }
    }
    
    // Tạo TOTP ban đầu với các giá trị mặc định
    setTimeout(() => {
        generateBtn.click();
    }, 100);
});
