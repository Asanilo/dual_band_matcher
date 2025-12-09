import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

# Import core logic
# Since this file is now in the root, we can import directly from core
import core.matcher
from core.matcher import find_all_designs

st.set_page_config(page_title="Dual Band Matching Design", layout="wide")

st.title("Dual Band Matching Network Designer")
st.markdown("Based on Pi-Network Synthesis and Conjugate Matching")

# Sidebar Inputs
st.sidebar.header("Design Parameters")

f1_ghz = st.sidebar.number_input("Frequency 1 (GHz)", value=0.9, step=0.05)
f2_ghz = st.sidebar.number_input("Frequency 2 (GHz)", value=1.2, step=0.05)

st.sidebar.subheader("Load Impedance @ f1")
r1 = st.sidebar.number_input("R1 (Ohm)", value=22.4)
x1 = st.sidebar.number_input("X1 (Ohm)", value=16.3)

st.sidebar.subheader("Load Impedance @ f2")
r2 = st.sidebar.number_input("R2 (Ohm)", value=26.2)
x2 = st.sidebar.number_input("X2 (Ohm)", value=20.3)

Z0 = st.sidebar.number_input("System Z0 (Ohm)", value=50.0)

st.sidebar.markdown("---")
st.sidebar.subheader("Constraints")
max_zn = st.sidebar.slider("Max Parallel Stub Impedance (Zn)", 50, 200, 105)

st.sidebar.markdown("---")
st.sidebar.markdown("**Auxiliary Elements**")
scan_load_aux = st.sidebar.checkbox("Enable Load-Side Aux Line Scan", value=True, help="Scans 0-180° for the auxiliary line at the load to satisfy Eq 3-10. If disabled, length is fixed to 0°.")
allow_aux_stub = st.sidebar.checkbox("Enable Case [c] Stub (at TL1 Input)", value=True, help="Controls the parallel stub added between TL1 and Pi-Network to handle Region [c] (R<=1, G<=1). This is NOT the auxiliary line at the load.")

if st.sidebar.button("Calculate Designs"):
    f1 = f1_ghz * 1e9
    f2 = f2_ghz * 1e9
    Z_L1 = complex(r1, x1)
    Z_L2 = complex(r2, x2)
    
    with st.spinner("Optimizing and searching for valid designs..."):
        results = find_all_designs(f1, f2, Z_L1, Z_L2, Z0, allow_aux_stub=allow_aux_stub, scan_load_aux_line=scan_load_aux)
    
    if not results:
        st.error("No valid designs found for these parameters.")
    else:
        df = pd.DataFrame(results)
        
        # Filter
        valid_df = df[df['Z_stub'] <= max_zn].copy()
        
        st.subheader(f"Found {len(df)} total designs, {len(valid_df)} meet constraints.")
        
        if not valid_df.empty:
            # Sort by closeness to 50 Ohm for Z_stub (manufacturability) or just show all
            valid_df['Delta_50'] = abs(valid_df['Z_stub'] - 50)
            valid_df = valid_df.sort_values('Delta_50')
            
            # Convert f_design to GHz for display
            valid_df['f_design'] = valid_df['f_design'] / 1e9
            
            # Define columns to format
            numeric_cols = ['f_design', 'Z_aux', 'theta_aux', 'Z1', 'theta1', 
                           'Z_series', 'Z_stub', 'aux_stub_Z', 'VSWR_f1', 'VSWR_f2', 'Delta_50']
            
            # Reorder columns to show region early
            cols_order = ['region', 'Z_stub', 'VSWR_f1', 'VSWR_f2', 'Z1', 'theta1', 'Z_series', 'theta_aux']
            # Add other columns that exist
            cols_order.extend([c for c in valid_df.columns if c not in cols_order])
            valid_df = valid_df[cols_order]

            # Apply formatting only to existing numeric columns
            format_dict = {col: "{:.2f}" for col in numeric_cols if col in valid_df.columns}
            if 'VSWR_f1' in format_dict: format_dict['VSWR_f1'] = "{:.4f}"
            if 'VSWR_f2' in format_dict: format_dict['VSWR_f2'] = "{:.4f}"
            
            st.dataframe(valid_df.style.format(format_dict))
            
            best = valid_df.iloc[0]
            st.success(f"Recommended Design: Zn = {best['Z_stub']:.2f} Ohm (Region: {best['region']})")
            
            # Detailed View
            st.markdown("### Detailed Parameters for Top Result")
            st.caption(f"Region: **{best['region']}** | Note: All electrical lengths (E) are defined at f_design = f1 + f2")
            
            # Check if Aux Stub exists (check if Z > 0 and type is valid)
            has_aux_stub = pd.notna(best['aux_stub_type']) and best['aux_stub_Z'] > 0
            
            cols = st.columns(4 if has_aux_stub else 3)
            
            with cols[0]:
                st.info("**1. Aux Line (TL_aux)**")
                st.write(f"Z = {best['Z_aux']:.2f} Ω")
                st.write(f"E = {best['theta_aux']:.2f}°")
                
            with cols[1]:
                st.info("**2. TL1 (Conjugate)**")
                st.write(f"Z = {best['Z1']:.2f} Ω")
                st.write(f"E = {best['theta1']:.2f}°")
                
            with cols[2]:
                st.info("**3. Pi-Network**")
                st.markdown("**Series Line:**")
                st.write(f"Z = {best['Z_series']:.2f} Ω")
                st.write(f"E = 180.00°")
                st.markdown("**Shunt Stubs:**")
                st.write(f"Z = {best['Z_stub']:.2f} Ω ({best['stub_type']})")
                st.write(f"E = 180.00°")

            if has_aux_stub:
                with cols[3]:
                    st.info("**4. Aux Stub (Case c)**")
                    st.write(f"Z = {best['aux_stub_Z']:.2f} Ω")
                    st.write(f"Type = {best['aux_stub_type']}")
                    st.write(f"E = 180.00°")
                
            st.metric("VSWR @ f1", f"{best['VSWR_f1']:.4f}")
            st.metric("VSWR @ f2", f"{best['VSWR_f2']:.4f}")
            
        else:
            st.warning("No designs meet the impedance constraint. Try increasing the Max Zn slider.")
            st.markdown("### All Valid Designs (Unfiltered)")
            
            # Convert f_design to GHz for display
            df['f_design'] = df['f_design'] / 1e9
            
            # Define columns to format
            numeric_cols = ['f_design', 'Z_aux', 'theta_aux', 'Z1', 'theta1', 
                           'Z_series', 'Z_stub', 'aux_stub_Z', 'VSWR_f1', 'VSWR_f2']
            
            # Apply formatting only to existing numeric columns
            format_dict = {col: "{:.2f}" for col in numeric_cols if col in df.columns}
            if 'VSWR_f1' in format_dict: format_dict['VSWR_f1'] = "{:.4f}"
            if 'VSWR_f2' in format_dict: format_dict['VSWR_f2'] = "{:.4f}"
            
            st.dataframe(df.style.format(format_dict))
