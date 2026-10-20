"""Package entrypoint for `python -m api_contract_diff`."""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
