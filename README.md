Banana 0.9: An Open-Source Medical Imaging System for Low-Resource Gastric Cancer Screening
Overview
Banana 0.9 is an open-source, modular medical imaging system designed for gastric cancer screening in low-resource environments. It provides GPU-free, Hounsfield Unit (HU)-based imaging segmentation for DICOM, NIfTI, or ZIP inputs, with optional support for multi-biomarker simulation (TriOx) and clinical risk factor integration. The system generates professional and patient-friendly reports, including text, JSON, and visualization outputs. Implemented in Python (≥3.13), it is validated using Monte Carlo simulations (10,000 runs) on the TCGA-STAD dataset [6]. This work extends our previous preprint [28] by providing a fully functional, reproducible implementation.
For full details, see the accompanying paper: Hu X. Banana 0.9: An Open-Source, Reproducible Medical Imaging System for Low-Resource Gastric Cancer Screening. 2025.
Features

HU-based Imaging Segmentation: Processes DICOM (.dcm), NIfTI (.nii, .nii.gz, .mgz, .mgh), or ZIP (.zip) files, using HU thresholding (default soft range: -250 to 200 HU, adjustable via CLI; visualization window: -200 to 400 HU) to segment gastric regions [7]. Outputs include NIfTI images, masks, and overlay PNGs.
Optional Modules: Supports TriOx biomarker simulation and clinical risk factor integration (not implemented in current main.py, controlled via --no-biomarker and --no-clinical flags in future versions).
Dual-Format Reporting: Generates:
Professional report (_report_pro.txt): Technical metrics (e.g., segmentation volume, HU threshold, voxel count).
Patient-friendly report (_report_easy.txt): Plain-language risk levels, size analogies (e.g., "grape size"), and clinical recommendations.
JSON report: Structured output for further processing.


Low-Resource Design: GPU-free, reducing computational requirements by >80% and rural screening costs by ~60% compared to GPU-based models.
Reproducibility: Full source code, sample data, and instructions available under CC BY-NC 4.0 at https://github.com/ohahouhui/Banana-0.9.

Installation
Python 3.13 on Windows is recommended. Other versions may require dependency adjustments.
1. Install dependencies
The setup.bat script automatically creates a virtual environment and installs dependencies. To install manually:
pip install -r requirements-py313.txt

Main dependencies (see References for citations):

numpy>=2.1.1 [8]
pydicom>=2.4.4 [11]
nibabel>=5.2.1 [10]
matplotlib>=3.8.4 [9]
tqdm>=4.66.4 [31]
fpdf2==2.7.9 [33]
Pillow==10.4.0 [32]
SimpleITK>=2.3.1 [12]
scipy>=1.14.1 [34] (optional, for connected-component analysis in segmentation)

2. Download sample data
Sample CT scans can be downloaded from The Cancer Imaging Archive (TCIA) TCGA-STAD collection [6] using the NBIA Data Retriever [19].
Usage
Run the main script (main.py) via the command-line interface (CLI). Example:
python main.py --input "path/to/input.nii.gz" --out "outputs"

CLI Parameters

--input: Path to input file (DICOM folder, ZIP, or NIfTI: .nii, .nii.gz, .mgz, .mgh) [required].
--out: Output directory for reports, NIfTI files, and PNGs [required].
--hu_lo: Visualization window lower bound (default: -200.0 HU).
--hu_hi: Visualization window upper bound (default: 400.0 HU).
--soft_lo: Soft threshold lower bound for segmentation (default: -250.0 HU).
--soft_hi: Soft threshold upper bound for segmentation (default: 200.0 HU).
--top_percent: Top percentile for thresholding (default: 0.60).
--z_smooth: Z-direction smoothing kernel size (default: 1).
--min_area: Minimum voxel count for connected-component analysis (default: 80, requires SciPy).

Example Output
For input case.nii.gz, outputs in the specified --out directory (e.g., outputs/case_20250905_123456_):

Professional Report (_report_pro.txt): Metrics including voxel volume, HU threshold, segmented volume (mm³ and ml), and file paths.
Patient-Friendly Report (_report_easy.txt): Risk level (e.g., "Low", "Medium", "High"), volume analogy (e.g., "grape size"), and clinical recommendations.
JSON Report (_report.json): Structured data with all metrics and paths.
NIfTI Files: Original image (_image.nii.gz) and binary mask (_image_mask.nii.gz).
Overlay PNG (_overlay_z50.png): Visualization of segmentation at middle slice.

System Architecture
The system comprises four modules, as shown in Figure 1:

HU-based imaging segmentation (implemented in main.py).
TriOx biomarker simulation (optional, not in current main.py).
Clinical risk factor integration (optional, not in current main.py).
Dual-format report generation (text and JSON, with PNG visualization).

Note: The paper describes a gastric-specific HU range (+20 to +70 HU [7]) for soft tissue segmentation, while main.py uses broader defaults (-250 to 200 HU for segmentation, -200 to 400 HU for visualization), adjustable via CLI parameters.
Validation
Performance was validated using Monte Carlo simulations (10,000 runs) on TCGA-STAD data [6], with parameters from literature (e.g., H. pylori prevalence [3]). Detection rates improved from 70% to 85% (urban) and 65% to 80% (rural). See Table 1 (Detection Rate Comparison) and Table 2 (Compute & Cost Analysis) in the paper.
Data & Code Availability
All code, sample data, and deployment instructions are available at https://github.com/ohahouhui/Banana-0.9 under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
Acknowledgments
Thanks to the TCGA-STAD consortium [6] and the open-source community for maintaining the software libraries used in this work.
References

World Health Organization. Cancer fact sheet. Published 2023. Accessed September 5, 2025. https://www.who.int/news-room/fact-sheets/detail/cancer  
Sung H, Ferlay J, Siegel RL, et al. Global cancer statistics 2020: GLOBOCAN estimates of incidence and mortality worldwide. CA Cancer J Clin. 2021;71(3):209-249. doi:10.3322/caac.21660  
Hooi JKY, Lai WY, Ng WK, et al. Global prevalence of Helicobacter pylori infection: systematic review and meta-analysis. Gastroenterology. 2017;153(2):420-429. doi:10.1053/j.gastro.2017.04.022  
Li P, Zeng W, Zhang Y, et al. Chinese national clinical practice guidelines on the prevention, screening, diagnosis, treatment, and follow-up of early gastric cancer. Chin Med J (Engl). 2024;137(8):969-993. doi:10.1097/CM9.0000000000003101  
Clark K, Vendt B, Smith K, et al. The Cancer Imaging Archive (TCIA): maintaining and operating a public information repository. J Digit Imaging. 2013;26(6):1045-1057. doi:10.1007/s10278-013-9622-7  
The Cancer Imaging Archive (TCIA). TCGA-STAD (Stomach Adenocarcinoma) collection. Published 2016. Accessed September 5, 2025. doi:10.7937/K9/TCIA.2016.GDHL9KIM  
Kalender WA. Computed Tomography: Fundamentals, System Technology, Image Quality, Applications. 3rd ed. Wiley; 2011.  
Harris CR, Millman KJ, van der Walt SJ, et al. Array programming with NumPy. Nature. 2020;585(7825):357-362. doi:10.1038/s41586-020-2649-2  
Hunter JD. Matplotlib: a 2D graphics environment. Comput Sci Eng. 2007;9(3):90-95. doi:10.1109/MCSE.2007.55  
NiBabel Developers. NiBabel: neuroimaging file I/O library (documentation). Accessed September 5, 2025. https://nipy.org/nibabel/  
pydicom contributors. Pydicom (DICOM file reader/writer) – software record. Zenodo. Published 2023. Accessed September 5, 2025. doi:10.5281/zenodo.8033898  
Lowekamp BC, Chen DT, Ibáñez L, Blezek D. The design of SimpleITK. Front Neuroinform. 2013;7:45. doi:10.3389/fninf.2013.00045  
Isensee F, Jaeger PF, Kohl SAA, Petersen J, Maier-Hein KH. nnU-Net: a self-configuring method for deep learning–based biomedical image segmentation. Nat Methods. 2021;18(2):203-211. doi:10.1038/s41592-020-01008-z  
Kamnitsas K, Ledig C, Newcombe VFJ, et al. Efficient multi-scale 3D CNN with fully connected CRF for accurate brain lesion segmentation. Med Image Anal. 2017;36:61-78. doi:10.1016/j.media.2016.10.004  
Fedorov A, Beichel R, Kalpathy-Cramer J, et al. 3D Slicer as an image computing platform for the Quantitative Imaging Network. Magn Reson Imaging. 2012;30(9):1323-1341. doi:10.1016/j.mri.2012.05.001  
Wilkinson MD, Dumontier M, Aalbersberg IJJ, et al. The FAIR Guiding Principles for scientific data management and stewardship. Sci Data. 2016;3:160018. doi:10.1038/sdata.2016.18  
Hosny A, Parmar C, Quackenbush J, Schwartz LH, Aerts HJWL. Artificial intelligence in radiology. Nat Rev Cancer. 2018;18(8):500-510. doi:10.1038/s41568-018-0016-5  
Willemink MJ, Koszek WA, Hardell C, et al. Preparing medical imaging data for machine learning. Radiology. 2020;295(1):4-15. doi:10.1148/radiol.2020192224  
National Cancer Institute. NBIA Data Retriever – download & user guide. Accessed September 5, 2025. https://wiki.cancerimagingarchive.net/display/NBIA/Downloading+TCIA+Images  
National Cancer Institute. Imaging Data Commons (IDC) portal – TCGA collections. Accessed September 5, 2025. https://imaging.datacommons.cancer.gov/  
Miki K. Gastric cancer screening using the serum pepsinogen test method. Gastric Cancer. 2006;9(4):245-253. doi:10.1007/s10120-006-0397-0  
Pasechnikov V, Chukov S, Fedorov E, et al. Gastric cancer: prevention, screening and early diagnosis. World J Gastroenterol. 2014;20(38):13842-13862. doi:10.3748/wjg.v20.i38.13842  
Shah SC, Wang AY, Wallace MB, Hwang JH. AGA clinical practice update on screening and surveillance in individuals at increased risk for gastric cancer in the United States: expert review. Gastroenterology. 2025;168(2):405-416.e1. doi:10.1053/j.gastro.2024.11.001  
Watabe H, Mitsushima T, Yamaji Y, et al. Predicting the development of gastric cancer from combining Helicobacter pylori antibodies and serum pepsinogen status: a prospective cohort study. Gut. 2005;54(6):764-768. doi:10.1136/gut.2004.055400  
Miki K. Gastric cancer screening by combined assay for serum anti-Helicobacter pylori IgG antibody and serum pepsinogen levels (“ABC method”). Proc Jpn Acad Ser B Phys Biol Sci. 2011;87(7):405-414. doi:10.2183/pjab.87.405  
Dondov G, Amarbayasgalan D, Batsaikhan B, et al. Diagnostic performances of pepsinogens and gastrin-17 for atrophic gastritis and gastric cancer in Mongolian subjects. PLoS One. 2022;17(10):e0274938. doi:10.1371/journal.pone.0274938  
Frija G, Blažić I, Frush DP, et al. How to improve access to medical imaging in low- and middle-income countries? eClinicalMedicine. 2021;38:101034. doi:10.1016/j.eclinm.2021.101034  
Hu X. A multi-modal AI-driven framework for early gastric cancer detection in low-income populations of developing countries. Research Square. Published 2025. Accessed September 5, 2025. doi:10.21203/rs.3.rs-7265963/v1  
Topol EJ. High-performance medicine: the convergence of human and artificial intelligence. Nat Med. 2019;25(1):44-56. doi:10.1038/s41591-018-0300-7  
Maier-Hein L, Eisenmann M, Reinke A, et al. Why rankings of biomedical image analysis competitions should be interpreted with care. Nat Commun. 2018;9:5217. doi:10.1038/s41467-018-07619-7  
Kluyver T, et al. tqdm: a fast, extensible progress bar for Python and CLI. Zenodo. Published 2023. Accessed September 5, 2025. doi:10.5281/zenodo.595120  
Clark A, et al. Pillow (PIL Fork) – Python Imaging Library. Zenodo. Published 2023. Accessed September 5, 2025. doi:10.5281/zenodo.7833042  
fpdf2 contributors. fpdf2: a Python library for PDF document generation. Zenodo. Published 2023. Accessed September 5, 2025. doi:10.5281/zenodo.10015162  
Virtanen P, Gommers R, Oliphant TE, et al. SciPy 1.0: fundamental algorithms for scientific computing in Python. Nat Methods. 2020;17(3):261-272. doi:10.1038/s41592-019-0686-2
