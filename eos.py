# The EoS specific information (CompOSE ID and the particle species entering
# the metatable) is not hardcoded here, but read from eos_config.json.

######################
# IMPORTS
######################
import json
import os
import re
import requests
import sys
from compose.eos import Metadata, Table
import argparse
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parent / "eos_config.json"
COMPOSE_URL = "https://compose.obspm.fr"
COMPOSE_FILES = ["eos.nb", "eos.t", "eos.yq", "eos.thermo", "eos.compo",
                 "eos.micro", "eos.init", "eos.mr", "eos.pdf"]

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

def complete_compose_url(url_or_id: str) -> str:
    '''
    Builds the URL of the webpage of an EoS from its CompOSE ID, e.g. 141 for
    https://compose.obspm.fr/eos/141. The full URL can be given as well.
    '''
    if "compose.obspm.fr" in url_or_id:
        id = url_or_id.split("/")[-1]
    else:
        # assume it is just the id
        id = url_or_id
    return f"{COMPOSE_URL}/eos/{id}"

def get_compose_download_url(url: str) -> tuple[str, str]:
    '''
    Reads the webpage of the EoS and returns its name and the URL of the folder
    its files are downloaded from, so that no URL has to be copied by hand.
    '''
    html = requests.get(url).text
    # find the line mentioning "eos.compo"

    pattern = r'<title>(.*)</title>'
    match = re.search(pattern, html)
    if match is not None:
        name = match.groups()[0].strip()
    else:
        name = "Unknown EoS"

    pattern = r'<a href="(/download/[^"]*?)/eos\.compo">eos\.compo</a>'
    matches = re.finditer(pattern, html)

    for match in matches:
        path = match.group(1)
        return name, f"{COMPOSE_URL}{path}"
    raise RuntimeError(f"Could not find the eos.compo file on page {url}.")

def get_compose_data(dl_url: str, outdir: str) -> str:
    '''
    Downloads the CompOSE files from the download folder of the EoS and returns
    the path of the folder they are stored in.
    '''
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    compose_dir = os.path.join(outdir, "compose")
    if not os.path.isdir(compose_dir):
        os.makedirs(compose_dir)

    for fn in COMPOSE_FILES:
        ff = requests.get(f"{dl_url}/{fn}")
        if not ff.ok: # not every table offers all of the files
            print(f"{fn} is not available, skipping it.")
            continue
        with open(os.path.join(compose_dir, fn), "wb") as f:
            f.write(ff.content)
    return compose_dir

def read_config(config_path: Path) -> dict:
    '''
    Reads the configuration file holding the known EoSs.

    Args:
        config_path: path to the JSON configuration file

    Returns:
        dictionary mapping the EoS key to its settings
    '''
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file {config_path} does not exist.")

    with open(config_path, "r") as f:
        return json.load(f)

def as_species(entries: dict) -> dict:
    '''
    Converts the species of the configuration file into the format expected by
    Metadata, i.e. {"10": ["n", "neutron"]} becomes {10: ("n", "neutron")}.
    JSON only allows for string keys, so the indices have to be cast to int.

    Args:
        entries: dictionary of species as read from the configuration file

    Returns:
        dictionary of tuples {index: (name, description)}
    '''
    return {int(index): tuple(value) for index, value in entries.items()}


def build_parser() -> argparse.ArgumentParser:
    '''
    Builds the command line interface. The defaults defined here are mirrored by
    the keyword arguments of run(), so that calling the script and importing it
    behave the same way.

    Returns:
        the argument parser of the script
    '''
    parser = argparse.ArgumentParser(description="Download and process EOS data")
    parser.add_argument("--output_dir", type=Path, help="Base directory where folders will be created")
    parser.add_argument("--download", action=argparse.BooleanOptionalAction, default=True, help="Whether to download the CompOSE data")
    parser.add_argument("--eos_name", type=str, help="Name of the equation of state as listed in the configuration file (e.g. SLy, SFHo, DD2)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help=f"JSON file with the EoS definitions (default: {DEFAULT_CONFIG})")
    parser.add_argument("--list_eos", action="store_true", help="List the EoSs available in the configuration file and exit")
    parser.add_argument("--hdf5", action="store_true", help="Enable HDF5 output")
    parser.add_argument("--athtab", action="store_true", help="Enable AthenaK table output")
    parser.add_argument("--lorene", action="store_true", help="Enable Lorene table output")
    parser.add_argument("--elliptica", action="store_true", help="Enable Elliptica table output")
    parser.add_argument("--elliptica_format", type=str, default="compose", choices=["compose", "geometric"],
                        help="Which format the Elliptica table takes")
    parser.add_argument("--elliptica_dcut", type=float, default=-1.0, help="Density cut on the Elliptica tables")
    parser.add_argument("--eos_cold", action="store_true", help="Enable cold EoS table output")
    parser.add_argument("--nqt", action="store_true", help="Enable NQT output")
    return parser

def list_eos(config: dict, config_path: Path = DEFAULT_CONFIG) -> None:
    '''
    Prints the EoSs defined in a configuration file together with the CompOSE
    webpage they are fetched from.

    Args:
        config: dictionary of EoS settings, as returned by read_config()
        config_path: path the configuration was read from, only used for the print

    Returns:
        None
    '''
    print(f"EoSs available in {config_path}:")
    for name, settings in config.items():
        print(f"  {name}: {complete_compose_url(str(settings['id']))}")

def run(eos_name: str,
        output_dir: str,
        config: Path = DEFAULT_CONFIG,
        download: bool = True,
        hdf5: bool = False,
        athtab: bool = False,
        lorene: bool = False,
        elliptica: bool = False,
        elliptica_format: str = "compose",
        elliptica_dcut: float = -1.0,
        eos_cold: bool = False,
        nqt: bool = False) -> Path:
    '''
    Fetches a CompOSE table and converts it into the requested formats.

    Args:
        eos_name: name of the EoS as listed in the configuration file
        output_dir: base directory, the folder <output_dir>/<eos_name> is created
        config: JSON file holding the EoS definitions
        download: whether to fetch the CompOSE data, or reuse an existing 'compose' folder
        hdf5, athtab, lorene, elliptica, eos_cold, nqt: which outputs to write
        elliptica_format: 'compose' or 'geometric', only used with elliptica
        elliptica_dcut: density cut of the Elliptica table, only used with elliptica

    Returns:
        path of the EoS folder holding the 'compose', 'athtab', 'hdf5', 'lorene'
        and 'elliptica' sub-directories that were requested

    Raises:
        ValueError: on an unknown EoS, an incompatible combination of outputs or
            missing CompOSE data
        FileNotFoundError: if the configuration file does not exist
    '''
    ######################
    # CONFIGURATION
    ######################
    # The EoS specific settings (CompOSE ID and the species of the metatable) are
    # read from the configuration file, so that this works for every EoS listed
    # in there.
    config_path = Path(config)
    settings = read_config(config_path)

    if eos_name not in settings:
        raise ValueError(f"EoS {eos_name} is not listed in {config_path}. "
                         f"Available: {', '.join(settings)}.")
    settings = settings[eos_name]

    # ID guards
    if (elliptica or lorene) and not eos_cold:
        raise ValueError("Lorene/Elliptica EOS format requires eos_cold!")

    ######################
    # PATHS
    ######################
    # Here, we specify the paths to the EoS folder that gets created, as well
    # as the sub-directories.
    base_path = Path(output_dir).expanduser()
    os.makedirs(base_path, exist_ok=True)
    print(f"Directory Path for EoS {eos_name}:", base_path)
    eos_path = Path(os.path.join(base_path, eos_name)) # full path to EoS folder

    create_directory(eos_path) # create the EoS directory

    if athtab: # athtab directory
        athtab_path = Path(os.path.join(eos_path, "athtab"))
        create_directory(athtab_path)

    if hdf5: # hdf5 directory
        hdf5_path = Path(os.path.join(eos_path, "hdf5"))
        create_directory(hdf5_path)

    if lorene: # Lorene directory
        lorene_path = Path(os.path.join(eos_path, "lorene"))
        create_directory(lorene_path)

    if elliptica: # Elliptica directory
        elliptica_path = Path(os.path.join(eos_path, "elliptica"))
        create_directory(elliptica_path)

    ######################
    # DATA
    ######################
    # The CompOSE ID for the specific EoS is stored in the configuration file. It
    # is the number at the end of the webpage of the EoS, in case of SLy
    # https://compose.obspm.fr/eos/141, so the ID is 141. The folder holding the
    # files is then looked up on that webpage, so that no download URL has to be
    # copied by hand.
    compose_path = Path(os.path.join(eos_path, "compose"))
    if download:
        compose_url = complete_compose_url(str(settings["id"]))
        create_directory(compose_path) # create the folder with the compose data

        # check whether there is already data present, otherwise fetch data
        has_files = any(compose_path.iterdir())
        if has_files:
            for file in compose_path.iterdir():  # iterates over all entries
                if file.is_file():               # only delete files, not subdirs
                    file.unlink()

        compose_name, dl_url = get_compose_download_url(compose_url)
        print(f"\nDownloading {compose_name} from {compose_url}")
        get_compose_data(dl_url, eos_path) # fetch the data
    else:
        if not os.path.exists(compose_path):
            raise ValueError("download is false, but the 'compose' folder " \
                             "does not exist!")
        else:
            for file in os.listdir(compose_path):
                if file in COMPOSE_FILES:
                    continue
                else:
                    raise ValueError(f"File '{file}' is missing in the compose folder!")

    ######################
    # EOS
    ######################
    # create the metatable from the species listed in the configuration file
    md = Metadata(
        pairs = as_species(settings.get("pairs", {})),
        quads = as_species(settings.get("quads", {})),
        micro = as_species(settings.get("micro", {}))
    )
    eos = Table(md)
    eos.read(compose_path, enforce_equal_spacing=True)

    # %%
    if settings.get("fix_electron_fraction", False):
        eos.Y['e'][:] = eos.yq[None, :, None] # electron fraction fix
    eos.compute_cs2(floor=1e-6)
    eos.compute_abar()
    eos.validate()

    # Remove the highest temperature point
    eos.restrict_idx(it1=-1)
    eos.shrink_to_valid_nb()

    # %%
    print("\nWriting EoS files from compose data...")
    if hdf5: eos.write_hdf5(hdf5_path / f"{eos_name}.h5")
    if athtab: eos.write_athtab(athtab_path / f"{eos_name}.athtab")

    # %% Take the lowest T slice of the EOS
    eos_cold_table = eos.slice_at_t_idx(0)
    # %% Find beta equilibrium
    eos_cold_table = eos_cold_table.make_beta_eq_table()

    # cold EoS output
    if eos_cold:
        print("Writing cold beta-equilibrium EoS files...")
        if hdf5: eos_cold_table.write_hdf5(hdf5_path / f"{eos_name}_T0.1_beta.h5")
        if lorene:
            eos_cold_table.write_lorene(lorene_path / f"{eos_name}_T0.1_beta.lorene")
            eos_cold_table.write_number_fractions(lorene_path / f"{eos_name}_T0.1_beta_Y.out")
        if athtab: eos_cold_table.write_athtab(athtab_path / f"{eos_name}_T0.1_beta.athtab")
        if elliptica:
            if elliptica_format == "compose":
                eos_cold_table.write_elliptica_compose(elliptica_path / f"{eos_name}_compose.txt", elliptica_dcut)
            if elliptica_format == "geometric":
                eos_cold_table.write_elliptica_geometric(elliptica_path / f"{eos_name}_geometric.txt", elliptica_dcut)

    # NQT format
    if nqt:
        print("Writing EoS NQT output...")
        eos_NQT = eos.make_NQT_version()
        if athtab:
            eos_NQT.write_athtab(athtab_path / f"{eos_name}_NQT.athtab")
        if hdf5:
            eos_NQT.write_hdf5(hdf5_path / f"{eos_name}_NQT.h5")

    return eos_path

def main(argv: list = None) -> int:
    '''
    Command line entry point. Parses the arguments and hands them to run().

    Args:
        argv: arguments to parse, sys.argv[1:] if not given

    Returns:
        exit code of the script
    '''
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_eos:
        list_eos(read_config(args.config), args.config)
        return 0

    if args.eos_name is None or args.output_dir is None:
        parser.error("--eos_name and --output_dir are required (use --list_eos to see the available EoSs).")

    options = vars(args)
    options.pop("list_eos")

    try:
        run(**options)
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        sys.exit(str(error))
    return 0

if __name__ == '__main__':
    sys.exit(main())
