from setuptools import find_packages, setup


setup(
    name="bml-price-lose-bot",
    version="0.1.0",
    description="Feishu bot for BML price lose detection.",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "apscheduler>=3.10.4",
        "eval-type-backport>=0.2.2; python_version < '3.10'",
        "fastapi>=0.111.0",
        "httpx>=0.27.0",
        "pydantic>=2.7.0",
        "pydantic-settings>=2.2.1",
        "python-dotenv>=1.0.1",
        "uvicorn[standard]>=0.30.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.2.0",
        ],
    },
)
