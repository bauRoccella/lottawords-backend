from setuptools import setup, find_packages

setup(
    name="lottawords",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "flask>=3.0.2",
        "selenium>=4.18.1",
        "python-dotenv>=1.0.1",
        "flask-cors>=4.0.0",
        "flask-caching>=2.1.0",
        "python-json-logger>=2.0.7",
        "apscheduler>=3.11.0",
        "pytz==2024.1",
        "tzdata==2024.1",
        "gunicorn>=21.2.0",
        "redis>=5.0.1",
        "webdriver-manager>=4.0.1",
        "setuptools>=69.0.0",
        "wheel>=0.42.0",
    ],
    include_package_data=True,
    package_data={
        "lottawords": ["templates/*.html"],
    },
) 