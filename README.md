# EOSympOSE
EOSympOSE is an easy-to-use extension of PyCompOSE (https://github.com/computationalrelativity/PyCompOSE), which is used to convert CompOSE (https://compose.obspm.fr/home/) equations of state into readable format for numerical relativity codes and initial data solvers.
EOSympOSE will automatically fetch the respective data from the CompOSE database and use the PyCompOSE tools to convert the data to the desired format. Examples for this also exists on the PyCompOSE repository, but here they are automatized for easy use-case and without downloading the data manually.

## Setting up PyCompOSE

When cloning EOSympOSE with

```bash
git clone https://github.com/spacetimecurv/EOSympOSE.git
```

PyCompOSE will automatically be added as a submodule. You might have to run

```bash
git submodule update --init --recursive
```

in the EOSympOSE root folder. To then build EOSympOSE and PyCompOSE run

```bash
pip install -e external/PyCompOSE -e .
```

This will build the library and enables all the functionality we might need.

## Usage
There is a single script, `eosympose.py`, which works for every EoS. Everything that is specific to an EoS (the CompOSE ID and the particle species entering the metatable) is not hardcoded, but read from the configuration file `eos_config.json`. For running, you have some options:

- eos_name: the name of the EoS as listed in the configuration file, also used for naming the files and directory (required)
- output_dir: the path to the directory, where the converted files and the CompOSE data are supposed to be stored (required)
- config: path to the JSON file holding the EoS definitions (`eos_config.json` next to `eosympose.py`, if not specified)
- list_eos: list the EoSs available in the configuration file and exit
- hdf5: flag for hdf5 output (false, if not specified)
- athtab: flag for athtab output (false, if not specified)
- lorene: flag for lorene output (false, if not specified)
- elliptica: flag for elliptica output (false, if not specified)
- elliptica_format: which format to write the elliptica table in ("compose"/"geometric"; works only with the elliptica flag)
- elliptica_dcut: density cut for the elliptica table in either format (works only with the elliptica flag)
- eos_cold: if a cold beta-equilibrium 1D temperature slice of a 3D table shall be created (works for 3D tables only)
- nqt: flag for nqt output (false, if not specified)

To see which EoSs are currently defined, type:

```bash
python eosympose.py --list_eos
```

If you desire the entire output, that is possible, the command would look like:

```bash
python eosympose.py --eos_name SLy --output_dir /path/to/dir --hdf5 --athtab --lorene --eos_cold --nqt --elliptica --elliptica_format compose --elliptica_dcut -1.0
```

This will first create a base folder under `/path/to/dir/SLy`, as well as four folders inside of the base directory, which are `compose` (holding the CompOSE data), `athtab` (holding the converted tables to .athtab format), `hdf5` (holding the converted tables to .h5 format), `lorene` (holding the converted tables to .lorene format and number fractions), and `elliptica` (holding the elliptica tables).

Then the program will fetch the data from the CompOSE library, using the CompOSE ID of the chosen EoS from `eos_config.json`. For the example of the `SLy` EoS, we use the data under https://compose.obspm.fr/eos/141, so the ID is 141 and the entry reads:

```json
"SLy": {
    "id": 141,
    "pairs": {
        "0": ["e", "electron"],
        "10": ["n", "neutron"],
        "11": ["p", "proton"],
        "4002": ["He4", "alpha particle"]
    },
    "quads": {},
    "fix_electron_fraction": true
}
```
The ID is simply the number at the end of the webpage of the EoS. The script visits that webpage, reads the download folder of the table off of it and then fetches the files `eos.nb`, `eos.t`, `eos.yq`, `eos.thermo`, `eos.compo`, `eos.micro`, `eos.init`, `eos.mr` and `eos.pdf` one by one. Files that a table does not offer are skipped. The data will be stored inside `compose`.

If all options were enabled, you will see the following files in the respective folders:

- athtab: `SLy_T0.1_beta.athtab` (1D temperature slice), `SLy.athtab` (full 3D table), `SLy_NQT.athtab` (NQT format)
- hdf5: `SLy_NQT.h5` (NQT format), `SLy_T0.1_beta.h5` (1D temperature slice), `SLy.h5` (full 3D table)
- lorene: `SLy_T0.1_beta.lorene` (1D temperature slice in Lorene format), `SLy_T0.1_beta_Y.out` (table with the number fractions)
- elliptica: `SLy_compose.txt` (1D temperature slice in elliptica CompOSE format), `SLy_geometric.txt` (1D temperature slice in elliptica geometric units format)

The NQT table is created directly from the table in memory, so `--nqt` writes it in whichever of the `--hdf5` and `--athtab` formats are enabled.


## Using it from Python

The same workflow is available as a function, so that `eosympose.py` can be driven from
another program instead of the command line. After installing the package, the
module is importable and `run()` takes the options above as keyword arguments,
with the same defaults as the flags:

```python
import eosympose

eos_path = eosympose.run(eos_name="SLy", output_dir="/path/to/dir",
                   hdf5=True, athtab=True, eos_cold=True,
                   elliptica=True, elliptica_format="compose",
                   elliptica_dcut=-1.0)
```

`run()` returns the path of the EoS folder it created, so that the converted
tables can be picked up afterwards:

```python
table = eos_path / "elliptica" / "SLy_compose.txt"
```

The options can be collected in a dictionary as well, which is handy when they
come from a configuration of their own:

```python
options = {"eos_name": "DD2", "output_dir": "/path/to/dir",
           "hdf5": True, "eos_cold": True}
eosympose.run(**options)
```

Errors are raised instead of exiting: an unknown EoS, an incompatible
combination of outputs (Elliptica or Lorene without `eos_cold`) or missing
CompOSE data raise `ValueError`, a configuration file that does not exist raises
`FileNotFoundError`. The EoSs of a configuration file can be listed with

```python
config = eosympose.read_config(eos.DEFAULT_CONFIG)
eosympose.list_eos(config)
```

## Other EoSs and data formats
Currently, the SLy, DD2, and SFHo EoS are defined in `eos_config.json`. If you wish to convert other CompOSE tables not listed there, then no just add another entry to the configuration file, with the CompOSE ID of the table and the particle species of the metatable. The keys of an entry are:

- id: the CompOSE ID of the EoS, i.e. the number at the end of its webpage (required, the full URL of the webpage works as well)
- pairs: the particles of the metatable, as `"index": ["name", "description"]` (optional)
- quads: the isotopes of the metatable, in the same format (optional)
- micro: the microphysics quantities of the metatable, in the same format (optional)
- fix_electron_fraction: sets the electron fraction to the charge fraction, needed for tables such as SLy (false, if not specified)

Note that JSON requires the indices to be quoted, they are cast back to integers when the metatable is built. An entry with the species

```json
"pairs": {
    "0": ["e", "electron"],
    "10": ["n", "neutron"],
    "11": ["p", "proton"],
    "4002": ["He4", "alpha particle"]
}
```

therefore results in the metatable

```python
md = Metadata(
    pairs = {
        0: ("e", "electron"),
        10: ("n", "neutron"),
        11: ("p", "proton"),
        4002: ("He4", "alpha particle")
    }
)
```

Which species are considered in a given EoS, can be found out in the `eos.pdf` summary on the CompOSE website of the EoS under consideration. Also, based on the utility of PyCompOSE, only `.h5`, `.athtab`, `.lorene`, and elliptica table formats are supported, which work with a multitude of codes.
