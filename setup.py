from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="paper2wechat",
    version="0.1.0",
    author="OSInsight",
    author_email="hello@osinsight.io",
    description="Convert Arxiv papers to WeChat Official Account articles with AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/OSInsight/paper2wechat",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "pydantic>=1.9.0",
        "pydantic-settings>=2.0.0",
        "pdfplumber>=0.9.0",
        "pypdf>=3.0.0",
        "PyMuPDF>=1.24.0",
        "PyYAML>=6.0",
        "anthropic>=0.7.0",
    ],
    entry_points={
        "console_scripts": [
            "paper2wechat=paper2wechat.core.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "paper2wechat": [
            "prompts/*.md",
            "templates/*.jinja2",
        ],
    },
)
