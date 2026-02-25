# PyCompOSE: manages CompOSE tables
# Copyright (C) 2022, David Radice <david.radice@psu.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Link to EoS: https://compose.obspm.fr/eos/18

######################
# IMPORTS
######################
import h5py
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
import os
import requests
import sys
from compose.eos import Metadata, Table
from compose.utils import convert_to_NQTs
import argparse
from pathlib import Path
import subprocess

def create_directory(path: str) -> None:
    '''
    This function creates a directory under the specified path.

    Args:
        path: string containing the path of the folder to be created

    Returns:
        None
    '''
    if os.path.isdir(path):
        print(f"Folder {path} already exists.")
    else:
        os.mkdir(path) # create the EoS directory
        print(f"Folder {path} created.")

def get_data(url: str, output_path: str) -> None:
    '''
    Downloads the data from the specified url.

    Args:
        url: string containing the url
        output_path: string containing the output path

    Returns:
        None
    '''
    print("\nDownloading EoS under URL:", url)
    response = requests.get(url, stream=True)
    response.raise_for_status()  # crash if download failed

    with open(output_path / "eos.zip", "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print("Downloaded:", url)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Download and process EOS data")
    parser.add_argument("--output_dir", type=Path, required=True, help="Base directory where folders will be created")
    parser.add_argument("--eos_name", type=str, required=True, help="Name of the equation of state (e.g. SLy, APR, DD2)")
    parser.add_argument("--hdf5", action="store_true", help="Enable HDF5 output")
    parser.add_argument("--athtab", action="store_true", help="Enable AthenaK table output")
    parser.add_argument("--lorene", action="store_true", help="Enable Lorene table output")
    parser.add_argument("--eos_cold", action="store_true", help="Enable cold EoS table output")
    parser.add_argument("--nqt", action="store_true", help="Enable NQT output")
    args = parser.parse_args()

    ######################
    # PATHS
    ######################
    # Here, we specify the paths to the EoS folder that gets created, as well
    # as the sub-directories.    
    eos_name = args.eos_name
    if os.path.isdir(args.output_dir): base_path = args.output_dir
    print(f"Directory Path for EoS {eos_name}:", base_path)
    eos_path = Path(os.path.join(base_path, eos_name)) # full path to EoS folder

    create_directory(eos_path) # create the EoS directory

    if args.athtab: # athtab directory
        athtab_path = Path(os.path.join(eos_path, "ATHTAB"))
        create_directory(athtab_path)

    if args.hdf5: # hdf5 directory
        hdf5_path = Path(os.path.join(eos_path, "HDF5"))
        create_directory(hdf5_path)

    if args.lorene: # Lorene directory
        lorene_path = Path(os.path.join(eos_path, "LORENE"))
        create_directory(lorene_path)

    ######################
    # DATA
    ######################
    # The URL for the specific EoS can be fetched, by going to the webpage of EoS,
    # in this case https://compose.obspm.fr/eos/141.
    # There one can usually enter the developer mode with F12. Change to the "Network" tab
    # and click on the eos.zip button for download. The .zip file should appear in the 
    # "Network" tab below. By clicking on the request, the full address is shown on the right
    # which can be copied here.
    url = "https://compose.obspm.fr/download//3D/Hempel_SchaffnerBielich/hs_dd2_compose/with_electrons/eos.zip"
    compose_path = Path(os.path.join(eos_path, "compose"))
    create_directory(compose_path) # create the folder with the compose data
    
    # check whether there is already data present, otherwise fetch data
    has_files = any(compose_path.iterdir())
    if has_files: 
        for file in compose_path.iterdir():  # iterates over all entries
            if file.is_file():               # only delete files, not subdirs
                file.unlink() 
    get_data(url, compose_path) # fetch the data

    # unzip the data
    subprocess.run(["unzip", f"{compose_path / "eos.zip"}", "-d", f"{compose_path}"], check=True)
    os.remove(compose_path / "eos.zip")

    ######################
    # EOS
    ######################
    # create the metatable
    md = Metadata(
    pairs = {
        0: ("e", "electron"),
        10: ("n", "neutro"),
        11: ("p", "proton"),
        4002: ("He4", "alpha particle"),
        3002: ("He3", "helium 3"),
        3001: ("H3", "tritium"),
        2001: ("H2", "deuteron")
    },
    quads = {
        999: ("N", "average nucleous")
    })
    eos = Table(md)
    eos.read(compose_path, enforce_equal_spacing=True)

    # %%
    eos.compute_cs2(floor=1e-6)
    eos.compute_abar()
    eos.validate()

    # Remove the highest temperature point
    eos.restrict_idx(it1=-1)
    eos.shrink_to_valid_nb()

    # %%
    print("\nWriting EoS files from compose data...")
    if args.hdf5: eos.write_hdf5(hdf5_path / f"{eos_name}.h5")
    if args.athtab: eos.write_athtab(athtab_path / f"{eos_name}.athtab")

    # %% Take the lowest T slice of the EOS
    eos_cold = eos.slice_at_t_idx(0)
    # %% Find beta equilibrium
    eos_cold = eos_cold.make_beta_eq_table()

    # cold EoS output
    if args.eos_cold:
        print("Writing cold beta-equilibrium EoS files...")
        if args.hdf5: eos_cold.write_hdf5(hdf5_path / f"{eos_name}_T0.1_beta.h5")
        if args.lorene:
            eos_cold.write_lorene(lorene_path / f"{eos_name}_T0.1_beta.lorene")
            eos_cold.write_number_fractions(lorene_path / f"{eos_name}_T0.1_beta_Y.out")
        if args.athtab: eos_cold.write_athtab(athtab_path / f"{eos_name}_T0.1_beta.athtab")

    # NQT format
    if args.nqt:
        print("Writing EoS NQT output...")
        input_table_fname  = f"{eos_name}.h5"
        output_table_fname = f"{eos_name}_NQT.h5"

        input_table_loc  = hdf5_path / input_table_fname
        output_table_loc = hdf5_path / output_table_fname

        if os.path.isfile(input_table_loc):
            convert_to_NQTs(input_table_loc, output_table_loc, NQT_order=2, use_bithacks=True)
        else:
            sys.exit(f"Make sure --hdf5 is enabled and {input_table_loc} exists.")

