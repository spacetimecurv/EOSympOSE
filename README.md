# EOSympOSE
EOSympOSE is an easy-to-use extension of PyCompOSE (https://github.com/computationalrelativity/PyCompOSE), which is used to convert CompOSE (https://compose.obspm.fr/home/) equations of state into readable format for numerical relativity codes and initial data solvers. 

EOSympOSE will automatically fetch the respective data from the CompOSE database and use the PyCompOSE tools to convert the data to the desired format. Examples for this also exists on the PyCompOSE repository, but here they are automatized for easy use-case and without downloading the data manually.

## Setting up PyCompOSE
Before using the scripts in this repository, the PyCompOSE utilities have to be cloned from https://github.com/computationalrelativity/PyCompOSE via:  

```git clone https://github.com/computationalrelativity/PyCompOSE```

To use all of the functionalities, such as NQTs, we have to make use of `setup.py` to build the NQT library. To do so, type the following inside of the root directory of PyCompOSE:  

```pip install -e .```

This will build the library and enables all the functionality we might need. Lastly, inside of the PyCompOSE root directory, create a folder called `scripts` or whatever other name you like. After changing into the `scripts` folder, clone the EOSympOSE repository by typing:  

```git clone https://github.com/spacetimecurv/EOSympOSE.git```

## Usage
Choose the script for the EoS that you want to convert, e.g. `SLy/SLy.py`. For running, you have some options:  

- eos_name: the name of the EoS, used for naming the files and directory (required)  
- output_dir: the path to the directory, where the converted files and the CompOSE data are supposed to be stored (required)  
- hdf5: flag for hdf5 output (false, if not specified)  
- athtab: flag for athtab output (false, if not specified)  
- lorene: flag for lorene output (false, if not specified)  
- eos_cold: if a cold beta-equilibrium 1D temperature slice of a 3D table shall be created (works for 3D tables only)  
- nqt: flag for nqt output (false, if not specified)

If you desire the entire output, that is possible, the command would look like:  

```python SLy.py --eos_name SLy --output_dir /path/to/dir --hdf5 --athtab --lorene --eos_cold --nqt```

This will first create a base folder under `/path/to/dir/SLy`, as well as four folders inside of the base directory, which are `compose` (holding the CompOSE data), `ATHTAB` (holding the converted tables to .athtab format), `HDF5` (holding the converted tables to .h5 format) and `LORENE` (holding the converted tables to .lorene format and number fractions).  

Then the program will fetch the data from the CompOSE library. For the example of the `SLy` EoS, we use the data under https://compose.obspm.fr/eos/141. Inside `SLy/SLy.py` we fetch and unzip the data with:  

```python
url = "https://compose.obspm.fr/download//3D/SRO/SLy4/eos.zip"
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
```
The URL to the `eos.zip` file can be obtained by visiting https://compose.obspm.fr/eos/141, entering developer mode with F12, changing to the `Network` tab and then clicking on the download button for `eos.zip`. In the `Network` tab, we will now see the URL by clicking on the request. In case of an older URL, 
follow these steps to change it or download the data manually. The unzipped data will now be stored inside `compose`.  

If all options were enabled, you will see the following files in the respective folders:  

- ATHTAB: `SLy_T0.1_beta.athtab` (1D temperature slice), `SLy.athtab` (full 3D table)
- HDF5: `SLy_NQT.h5` (NQT format), `SLy_T0.1_beta.h5` (1D temperature slice), `SLy.h5` (full 3D table)
- LORENE: `SLy_T0.1_beta.lorene` (1D temperature slice in Lorene format), `SLy_T0.1_beta_Y.out` (table with the number fractions)

If you also wish to have `SLy_NQT.athtab`, then use the script `hdf5toathtab.py` under https://github.com/jfields7/table-reader/tree/main/tools to convert `SLy_NQT.h5` into `.athtab` format. For this, type:  

```python hdf5toathtab.py --input /path/to/SLy_NQT.h5 --output /path/to/SLy_NQT.athtab```


## Other EoSs and data formats
Currently, only the SLy, DD2, and SFHo EoS are given here. If you wish to convert other CompOSE tables not listed here, then use the given scripts as a template and only change the URL as described above and the metatable with the particle species:  

```python
md = Metadata(
    pairs = {
        0: ("e", "electron"),
        10: ("n", "neutro"),
        11: ("p", "proton"),
        4002: ("He4", "alpha particle")
    }
)
```

Which species are considered in a given EoS, can be found out in the `eos.pdf` summary on the CompOSE website of the EoS under consideration. Also, based on the utility of PyCompOSE, only `.h5`, `.athtab`, and `.lorene` formats are supported, which work with a multitude of codes.
