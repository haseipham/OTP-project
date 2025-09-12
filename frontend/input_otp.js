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

        function checkOtp() {
            const otpCode = Array.from(otpInputs).map(input => input.value).join('');
            if (otpCode.length === 6) {
                alert('Mã OTP đã nhập: ' + otpCode);
            } else {
                alert('Vui lòng nhập đủ 6 chữ số của mã OTP.');
            }
        }