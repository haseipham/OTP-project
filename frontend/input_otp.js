document.addEventListener('DOMContentLoaded', function() {
    const otpInputs = document.querySelectorAll('.otp-input');

    otpInputs.forEach((input, index) => {
        input.addEventListener('input', () => {
            const value = input.value;
            if (value.length === 1 && index < otpInputs.length - 1) {
                otpInputs[index + 1].focus();
            } else if (value.length > 1) {
                input.value = value.charAt(0);
            }
        });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && input.value === '' && index > 0) {
                otpInputs[index - 1].focus();
            }
        });
    });
});

async function checkOtp() {
            const otpInputs = document.querySelectorAll('.otp-input');
            const otpCode = Array.from(otpInputs).map(input => input.value).join('');
            if (otpCode.length !== 6) {
                alert('Vui lòng nhập đủ 6 chữ số của mã OTP.');
                return;
            }

            const username = localStorage.getItem('username');
            if (!username) {
                alert('User not found. Please login again.');
                window.location.href = 'Login.html';
                return;
            }

            try {
                const response = await fetch('/api/v2/verify_totp/' + username, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ code: otpCode })
                });

                const data = await response.json();
                if (response.ok && data.valid) {
                    alert('OTP verified successfully');
                    window.location.href = 'congratulations.html';
                } else {
                    alert('Invalid OTP code');
                }
            } catch (error) {
                alert('Error verifying OTP: ' + error.message);
            }
        }