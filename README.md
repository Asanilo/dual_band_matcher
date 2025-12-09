# Dual Band Matching Designer
[English](./README.md) | [中文文档](./README_CN.md)
A Streamlit-based tool for designing dual-band impedance matching networks using Pi-network synthesis and conjugate matching techniques.

## Features
![image](image.png)
- **Dual-Band Matching**: Supports arbitrary frequency pairs.
- **Parameter Scanning**: Automatically scans auxiliary transmission line lengths to find optimal solutions.
- **Interactive Filtering**: Filter designs based on manufacturability constraints (e.g., max impedance).
- **Detailed Reports**: Provides full electrical parameters for all transmission lines.

##  Streamlit Community Cloud

This app is deployed on Streamlit Cloud for easy sharing.
[Streamlit WebApp is here.](https://asanilo-dual-band-matcher-streamlit-app-ghopyu.streamlit.app/)

## Local Development

To run the app locally:

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the app:
    ```bash
    streamlit run streamlit_app.py
    ```
