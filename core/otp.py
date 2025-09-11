# python -m otp instead of python -m otp_cli
"""
Program now no longer: python -m otp init
Use: python -m otp init --user USERNAME 
and the --user argument is required for all commands.
"""
from otp_cli import (
    main,
)
if __name__ == "__main__":
    main()