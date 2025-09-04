
```markdown
# Banana 0.9: An Open-Source, Reproducible Medical Imaging System for Low-Resource Gastric Cancer Screening

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC_BY--NC_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

## Overview
**Banana 0.9** is a fully open-source, reproducible medical imaging system designed for gastric cancer CT screening in low-resource settings.  
It is a lightweight, CPU-friendly implementation that provides the core functionality described in the author’s earlier research, optimized for reproducibility and easy deployment.

⚠ **Disclaimer**: This tool is a research prototype and **not** intended for clinical diagnosis.

Key features:
- **GPU-Free**: Runs on standard CPU hardware, no high-end GPU required.
- **Multi-format input**: Supports DICOM, NIfTI, and ZIP files.
- **Automatic dual-report generation**:
  - Professional report (`_report_pro.txt`)
  - Patient-friendly summary (`_report_easy.txt`)
- **Lightweight & reproducible**: Includes a minimal sample dataset for one-click execution.

---

## Directory Structure
```

Banana0.9/
├── main.py                  # Main inference script (outputs Chinese reports)
├── run\_py313.bat             # One-click execution script for Windows
├── requirements-py313.txt    # Python dependencies (for Python 3.13)
├── sample\_data/
│   └── 2.000000-AXIAL SC-25389.zip   # Minimal example dataset
├── outputs/                  # Output directory (auto-generated)
└── README.md

````

---

## Installation
Python 3.13 on Windows is recommended. Other versions may require dependency adjustments.

### 1. Install dependencies
The `.bat` script will automatically create a virtual environment and install dependencies.  
To install manually:
```bash
pip install -r requirements-py313.txt
````

Main dependencies:

* numpy
* pydicom
* nibabel
* matplotlib
* tqdm
* fpdf2
* Pillow
* SimpleITK

---

## Quick Start

1. **Clone this repository**

```bash
git clone https://github.com/ohahouhui/Banana-0.9
cd Banana0.9
```

2. **Run the one-click script**

```bash
Double-click run_py313.bat
```

3. **Check the output**

* Output directory: `outputs/`
* Professional report: `*_report_pro.txt`
* Patient-friendly summary: `*_report_easy.txt`
* Overlay image: `*_overlay_z50.png`

---

## Data Source

The example dataset is derived from **The Cancer Imaging Archive (TCIA)** gastric cancer cases.

> Citation:
> The Cancer Imaging Archive (TCIA). [https://www.cancerimagingarchive.net/](https://www.cancerimagingarchive.net/)

For additional cases, download from TCIA using the **NBIA Data Retriever** tool.

---

## License

This project is released under the **[Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)** license:

* **BY**: Attribution required
* **NC**: Non-commercial use only
* You may share and adapt the work, but commercial use is prohibited.

---

## References

This project is the open-source, runnable follow-up implementation of the following preprint:

Hu X. **A Multi-Modal AI-Driven Framework for Early Gastric Cancer Detection in Low-Income Populations of Developing Countries**. *Research Square*, 2025.
[https://doi.org/10.21203/rs.3.rs-7265963/v1](https://doi.org/10.21203/rs.3.rs-7265963/v1)

> Note: The preprint used Alibaba DAMO Academy’s **GRAPE** early screening model for demonstration.
> Banana 0.9 is an independently developed, lightweight, and reproducible version created afterward by the same author, based on public datasets and optimized for deployment in low-resource environments.

```


```
