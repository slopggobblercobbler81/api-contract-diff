from setuptools import setup, find_packages

setup(
    name="api-contract-diff",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "api-contract-diff=api_contract_diff.cli:main",
            "contract-diff=api_contract_diff.cli:main",
        ],
    },
)
