"""
This module contains a collection of general functions used across this library, that is to say if a method ends up here
it is because it is useful in more than one context.

Some of the modules in this library that depend on this module are:

- :meth:`pypet2bids.convert_pmod_to_blood`
- :meth:`pypet2bids.dcm2niix4pet`
- :meth:`pyet2bids.read_ecat`
- :meth:`pypet2bids.ecat`
- :meth:`pypet2bids.ecat2nii`
- :meth:`pypet2bids.multiple_spreadsheets`

| *Authors: Anthony Galassi*
| *Copyright OpenNeuroPET team*
"""

import os
import gzip
import re
import shutil
import typing
import json
import hashlib
import warnings
import logging
import dotenv
import ast
import sys
import subprocess

import numpy
import pandas
import toml
import pathlib
from pandas import read_csv, read_excel, Series
from pathlib import Path
import importlib
import argparse
from typing import Union
from platform import system

parent_dir = pathlib.Path(__file__).parent.resolve()
project_dir = parent_dir.parent.parent
if "PET2BIDS" not in project_dir.parts:
    project_dir = parent_dir

metadata_dir = os.path.join(project_dir, "metadata")

# check to see where the schema is at
pet_metadata_json = os.path.join(metadata_dir, "PET_metadata.json")
permalink_pet_metadata_json = "https://github.com/openneuropet/PET2BIDS/blob/76d95cf65fa8a14f55a4405df3fdec705e2147cf/metadata/PET_metadata.json"
pet_reconstruction_metadata_json = os.path.join(
    metadata_dir, "PET_reconstruction_methods.json"
)

# load bids schema
bids_schema_path = os.path.join(metadata_dir, "schema.json")
schema = json.load(open(bids_schema_path, "r"))

# putting these paths here as they are reused in dcm2niix4pet.py, update_json_pet_file.py, and ecat.py
module_folder = Path(__file__).parent.resolve()
python_folder = module_folder.parent
pet2bids_folder = python_folder.parent
metadata_folder = os.path.join(pet2bids_folder, "metadata")

loggers = {}


def logger(name):
    global loggers
    if loggers.get(name):
        return loggers.get(name)
    else:
        # create logger with for pypet2bids
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(logging.DEBUG)

        ch.setFormatter(CustomFormatter())

        logger.addHandler(ch)
        # this stops the logger from repeating itself in the outputs, it's most likely set up incorrectly, but this
        # works great to get the desired effect
        logger.propagate = False

        loggers[name] = logger
        return logger


def load_pet_bids_requirements_json(
    pet_bids_req_json: Union[str, pathlib.Path] = pet_metadata_json
) -> dict:
    if type(pet_bids_req_json) is str:
        pet_bids_req_json = pathlib.Path(pet_bids_req_json)
    if pet_bids_req_json.is_file():
        with open(pet_bids_req_json, "r") as infile:
            reqs = json.load(infile)
        return reqs
    else:
        raise FileNotFoundError(pet_bids_req_json)


def flatten_series(series):
    """
    This function retrieves either a list or a single value from a pandas series object thus converting a complex
    data type to a simple datatype or list of simple types. If the length of the series is one or less this returns that
    single value, else this object returns all values within the series that are not Null/nan in the form of a list
    :param series: input series of type pandas.Series object, typically extracted as a column/row from a
    pandas.Dataframe object
    :return: a simplified single value or list of values
    """
    simplified_series_object = series.dropna().to_list()
    if len(simplified_series_object) > 1:
        pass
    elif len(simplified_series_object) == 1:
        simplified_series_object = simplified_series_object[0]
    else:
        raise Exception(f"Invalid Series: {series}")
    return simplified_series_object


def collect_spreadsheets(folder_path: pathlib.Path):
    spreadsheet_files = []
    all_files = [
        folder_path / pathlib.Path(file)
        for file in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, file))
    ]
    for file in all_files:
        if (
            file.suffix == ".xlsx"
            or file.suffix == ".csv"
            or file.suffix == ".xls"
            or file.suffix == ".tsv"
        ):
            spreadsheet_files.append(file)
    return spreadsheet_files


def single_spreadsheet_reader(
    path_to_spreadsheet: Union[str, pathlib.Path],
    pet2bids_metadata_json: Union[str, pathlib.Path] = pet_metadata_json,
    dicom_metadata={},
    **kwargs,
) -> dict:

    metadata = {}

    if type(path_to_spreadsheet) is str:
        path_to_spreadsheet = pathlib.Path(path_to_spreadsheet)

    if path_to_spreadsheet.is_file():
        pass
    else:
        raise FileNotFoundError(f"{path_to_spreadsheet} does not exist.")

    if pet2bids_metadata_json:
        if type(pet_metadata_json) is str:
            pet2bids_metadata_json = pathlib.Path(pet2bids_metadata_json)

        if pet2bids_metadata_json.is_file():
            with open(pet_metadata_json, "r") as infile:
                metadata_fields = json.load(infile)
        else:
            raise FileNotFoundError(
                f"Required metadata file not found at {pet_metadata_json}, check to see if this file exists;"
                f"\nelse pass path to file formatted to this {permalink_pet_metadata_json} via "
                f"pet2bids_metadata_json argument in simplest_spreadsheet_reader call."
            )
    else:
        raise FileNotFoundError(
            f"pet2bids_metadata_json input required for function call, you provided {pet2bids_metadata_json}"
        )

    spreadsheet_dataframe = open_meta_data(path_to_spreadsheet)

    log = logging.getLogger("pypet2bids")

    # collect mandatory fields
    for field_level in metadata_fields.keys():
        for field in metadata_fields[field_level]:
            series = spreadsheet_dataframe.get(field, Series(dtype=numpy.float64))
            if not series.empty:
                metadata[field] = flatten_series(series)
            elif (
                series.empty
                and field_level == "mandatory"
                and not dicom_metadata.get(field, None)
                and field not in kwargs
            ):
                log.warning(
                    f"{field} not found in metadata spreadsheet: {path_to_spreadsheet}, {field} is required by BIDS"
                )

    # lastly apply any kwargs to the metadata
    metadata.update(**kwargs)

    # more lastly, check to see if values are of the correct datatype (e.g. string, number, boolean)
    for field, value in metadata.items():
        # check schema for field
        field_schema_properties = schema["objects"]["metadata"].get(field, None)
        if field_schema_properties:
            # check to see if value is of the correct type
            if field_schema_properties.get("type") == "number":
                if not is_numeric(str(value)):
                    log.warning(f"{field} is not numeric, it's value is {value}")
            if field_schema_properties.get("type") == "boolean":
                if type(value) is not bool:
                    try:
                        check_bool = int(value) / 1
                        if check_bool == 0 or check_bool == 1:
                            metadata[field] = bool(value)
                        else:
                            log.warning(
                                f"{field} is not boolean, it's value is {value}"
                            )
                    except ValueError:
                        pass
            elif field_schema_properties.get("type") == "string":
                if type(value) is not str:
                    log.warning(f"{field} is not string, it's value is {value}")
            else:
                pass
    return metadata


def compress(file_like_object, output_path: str = None):
    """
    Compresses a file using gzip.

    :param file_like_object: a file path to an uncompressed file
    :param output_path: an output path to compress the file to, if omitted simply appends .gz to
        file_like_object path
    :return: output_path on successful completion of compression
    """
    file_like_object = pathlib.Path(file_like_object)

    if file_like_object.exists() and not output_path:
        old_suffix = file_like_object.suffix
        if ".gz" not in old_suffix:
            output_path = file_like_object.with_suffix(old_suffix + ".gz")
        else:
            output_path = file_like_object

    elif not os.path.isfile(file_like_object):
        raise Exception(f"{file_like_object} is not a valid file to compress.")
    else:
        pass

    with open(file_like_object, "rb") as infile:
        input_data = infile.read()

    output = gzip.GzipFile(output_path, "wb")
    output.write(input_data)
    output.close()

    if output_path.exists():
        file_like_object.unlink(missing_ok=True)

    return output_path


def decompress(file_like_object, output_path: str = None):
    """
    Decompresses a gzip file.

    :param file_like_object: a compressed gzip file
    :param output_path: optional output path, if not supplied this function simply trims '.gz' off of
        the input file and writes to that amended path
    :return: output_path on successful decompression
    """
    if not output_path and ".gz" in file_like_object:
        output_path = re.sub(".gz", "", file_like_object)

    compressed_file = gzip.GzipFile(file_like_object)
    compressed_input = compressed_file.read()
    compressed_file.close()

    with open(output_path, "wb") as outfile:
        outfile.write(compressed_input)
    return output_path


def load_vars_from_config(path_to_config: str):
    """
    Loads values from a .env file given a path to said .env file.

    :param path_to_config: path to .env file
    :return: a dictionary containing the values stored in .env
    """
    if os.path.isfile(path_to_config):
        parameters = dotenv.main.dotenv_values(path_to_config)
    else:
        raise FileNotFoundError(path_to_config)

    for parameter, value in parameters.items():
        try:
            parameters[parameter] = very_tolerant_literal_eval(value)
        except (ValueError, SyntaxError):
            parameters[parameter] = str(value)

    return parameters


def get_version():
    """
    Gets the version of this software from the toml file
    :return: version number from pyproject.toml
    """
    # this scripts directory path
    scripts_dir = pathlib.Path(os.path.dirname(__file__))

    try:
        # if this is bundled as a package look next to this file for the pyproject.toml
        toml_path = os.path.join(scripts_dir, "pyproject.toml")
        with open(toml_path, "r") as infile:
            tomlfile = toml.load(infile)
    except FileNotFoundError:
        # when in development the toml file with the version is 2 directories above (e.g. where it should actually live)
        toml_dir = scripts_dir.parent
        toml_path = os.path.join(toml_dir, "pyproject.toml")
        with open(toml_path, "r") as infile:
            tomlfile = toml.load(infile)

    attrs = tomlfile.get("tool", {})
    poetry = attrs.get("poetry", {})
    version = poetry.get("version", "")

    return version


def is_numeric(check_this_object: str) -> bool:
    try:
        converted_to_num = ast.literal_eval(check_this_object)
        numeric_types = [int, float, pandas.NA]
        if type(converted_to_num) in numeric_types:
            return True
    except (ValueError, TypeError):
        return False


class ParseKwargs(argparse.Action):
    """
    Class that is used to extract key pair arguments passed to an argparse.ArgumentParser object via the command line.
    Accepts key value pairs in the form of 'key=value' and then passes these arguments onto the arg parser as kwargs.
    This class is used during the construction of the ArgumentParser class via the add_argument method. e.g.:\n
    `ArgumentParser.add_argument('--kwargs', '-k', nargs='*', action=helper_functions.ParseKwargs, default={})`
    """

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, dict())
        for value in values:
            try:
                key, value = value.split("=")
                getattr(namespace, self.dest)[key] = very_tolerant_literal_eval(value)
            except ValueError:
                raise Exception(f"Unable to unpack {value}")


def very_tolerant_literal_eval(value):
    """
    Evaluates a string or string like input into a python datatype. Provides a lazy way to extract True from 'true',
    None from 'none', [0] from '[0'], etc. etc.
    :param value: the value you wish to convert to a python type
    :type value: string like, could be anything that can be evaluated as valid python
    :return: the value converted into a python object
    :rtype: depends on what ast.literal_eval determines the object to be
    """
    try:
        value = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        if str(value).lower() == "none":
            value = None
        elif str(value).lower() == "true":
            value = True
        elif str(value).lower() == "false":
            value = False
        elif str(value)[0] == "[" and str(value)[-1] == "]":
            array_contents = str(value).replace("[", "").replace("]", "")
            array_contents = array_contents.split(",")
            array_contents = [str.strip(content) for content in array_contents]
            # evaluate array contents one by one
            value = [very_tolerant_literal_eval(v) for v in array_contents]
        else:
            value = str(value)
    return value


def open_meta_data(
    metadata_path: Union[str, pathlib.Path], separator=None
) -> pandas.DataFrame:
    """
    Opens a text metadata file with the pandas method most appropriate for doing so based on the metadata
    file's extension.
    :param metadata_path: Path or pathlike object/string to a spreadsheet file
    :type metadata_path: Path or str
    :param separator: Optional seperator argument, used to try and parse tricky spreadsheets. e.g. ',' '\t', ' '
    :type separator: str
    :return: a pandas dataframe representation of the spreadsheet/metadatafile
    """
    log = logger("pypet2bids")
    if type(metadata_path) is str:
        metadata_path = pathlib.Path(metadata_path)

    separators_present = []
    if metadata_path.exists():
        pass
    else:
        raise FileExistsError(metadata_path)

    # collect suffix from metadata and use the approriate pandas method to read the data
    extension = metadata_path.suffix

    methods = {"excel": read_excel, "csv": read_csv, "tsv": read_csv, "txt": read_csv}

    if "xls" in extension or "bld" in extension:
        proper_method = "excel"
    else:
        proper_method = extension.replace(".", "")
        with open(metadata_path, "r") as infile:
            first_line = infile.read()
            # check for separators in line
            separators = ["\t", ","]
            for sep in separators:
                if sep in first_line:
                    separators_present.append(sep)

    try:
        warnings.filterwarnings("ignore", message="ParserWarning: Falling*")
        use_me_to_read = methods.get(proper_method, None)

        if proper_method != "excel":
            if "\t" in separators_present:
                separator = "\t"
            else:
                separator = ","
            metadata_dataframe = use_me_to_read(metadata_path, sep=separator)
        else:
            metadata_dataframe = use_me_to_read(metadata_path, sheet_name=None)
            # check to see if there are multiple sheets in this input file
            multiple_sheets = pandas.ExcelFile(metadata_path).sheet_names
            first_sheet = multiple_sheets.pop(0)
            if len(multiple_sheets) >= 1:
                for index, sheet_name in enumerate(multiple_sheets):
                    for column in metadata_dataframe[sheet_name].columns:
                        metadata_dataframe[first_sheet][column] = metadata_dataframe[
                            sheet_name
                        ][column]

            metadata_dataframe = metadata_dataframe[first_sheet]

    except (IOError, ValueError) as err:
        try:
            metadata_dataframe = pandas.read_csv(
                metadata_path, sep=separator, engine="python"
            )
        except IOError:
            log.error(
                f"Tried falling back to reading {metadata_path} with pandas.read_csv, still unable to parse"
            )
            raise err(f"Problem opening {metadata_path}")

    return metadata_dataframe


def translate_metadata(metadata_path, metadata_translation_script_path, **kwargs):
    log = logger("pypet2bids")
    # load metadata
    metadata_dataframe = open_meta_data(metadata_path)

    if metadata_dataframe is not None:
        try:
            # this is where the goofiness happens, we allow the user to create their own custom script to manipulate
            # data from their particular spreadsheet wherever that file is located.
            spec = importlib.util.spec_from_file_location(
                "metadata_translation_script_path", metadata_translation_script_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # note the translation must have a method named translate metadata in order to work
            text_file_data = module.translate_metadata(metadata_dataframe, **kwargs)
        except AttributeError as err:
            log.warning(f"Unable to locate metadata_translation_script\n{err}")
    else:
        log.info(f"No metadata found at {metadata_path}")
        text_file_data = None

    return text_file_data


def import_and_write_out_module(module: str, destination: str):
    """
    Writes an imported module file to a destination
    :param module: an imported python module
    :param destination: the destination to write the source/script of the module to file

    :return: the destination path of the copied module file if successful
    """
    imported_module = importlib.import_module(module)
    path_to_module = os.path.abspath(imported_module.__file__)
    shutil.copy(path_to_module, destination)
    if os.path.isfile(destination):
        return destination
    elif os.path.isdir(destination):
        return os.path.join(destination, os.path.basename(path_to_module))


def write_out_module(module: str = "pypet2bids.metadata_spreadsheet_example_reader"):
    parser = argparse.ArgumentParser(
        description="[DEPRECATED!!] Write out a template for a python script used for "
        "bespoke metadata."
    )
    parser.add_argument(
        "template_path",
        type=str,
        help="Path to write out template for a translation script.",
    )
    args = parser.parse_args()

    import_and_write_out_module(module=module, destination=args.template_path)


def expand_path(path_like: str) -> str:
    """
    Expands relative ~ paths to full paths

    :param path_like: path like string
    :type path_like: string

    :return: full path string
    :rtype: string
    """
    if path_like:
        if path_like[0] == "~":
            return str(os.path.expanduser(path_like))
        else:
            return os.path.abspath(path_like)
    else:
        return ""


def collect_bids_part(bids_part: str, path_like: Union[str, pathlib.Path]) -> str:
    """
    Regex is hard, this finds a bids key if it's present in path or pathlink string

    >>> bids_like_path = '/home/users/user/bids_data/sub-NDAR123/ses-firstsession'
    >>> subject_id = collect_bids_part('sub', bids_like_path)
    >>> subject_id
    >>> "sub-NDAR123"

    :param bids_part: the bids part to find in the path e.g. subject id, session id, recording, etc etc
    :type bids_part: string
    :param path_like: a pathlike input, this is strictly for parsing file paths or file like strings
    :type path_like: string or pathlib.Path object, we don't descriminate
    :return: the collected bids part
    :rtype: string
    """
    log = logger("pypet2bids")

    # get os of system
    if os.name == "posix":
        not_windows = True
    else:
        not_windows = False

    # break up path into parts
    parts = pathlib.PurePath(path_like).parts

    # this shouldn't happen, but we check if someone passed a windows path to a posix machine
    # should we check for the inverse? No, not until someone complains about this loudly enough.
    for part in parts:
        if "\\" in part and not_windows:
            # explicitly use windows path splitting
            parts = pathlib.PureWindowsPath(path_like).parts
            log.warning(
                f"Detected \\ in BIDS like path {path_like}, but os is {os.name}, doing best to parse."
            )
            break

    # create search string
    search_string = bids_part + "-(.*)"
    # collect bids_part
    for part in parts:
        found_part = re.search(search_string, part)
        if found_part:
            collected_part = found_part[0]
            break
        else:
            collected_part = ""

    if "_" in collected_part:
        parts = collected_part.split("_")
        for part in parts:
            found_part = re.search(search_string, part)
            if found_part:
                collected_part = found_part[0]
                break
            else:
                collected_part = ""

    return collected_part


def get_coordinates_containing(
    containing: typing.Union[str, int, float],
    dataframe: pandas.DataFrame,
    exact: bool = False,
    single=False,
) -> typing.Union[list, tuple]:
    """
    Collects the co-ordinates (row and column) containing an input value, that value could be a string, integer, or
    float. When searching for integers or floats it is most likely best to use set the exact argument to True; the same
    goes for finding the exact match of a string. This method is primarily meant to find the row corresponding to a
    subject ID, e.g.

    if your dataframe is given as

    subject_id    some_values    more_values
    sub-NDAR1     1              2
    sub-NDAR2     3              3

    And you provided the arguments: `containing='sub-NDAR', exact=False` you would return a set of the following
    co-ordinates

    [(0, 'subject_id'), (1, 'subject_id')]

    If you are confident in your input data you would most likely call this method this way:

    >>> coordinates = get_coordinates_containing(
    >>>    'sub-NDAR1',
    >>>    pandas.DataFrame({'subject_id': ['sub-NDAR1', 'sub-NDAR2'], 'some_values': [1, 2]}),
    >>>    single=True)
    >>> coordinates
    >>> (0, 1)

    :param containing: value you wish to search a dataframe for
    :type containing: string, integer, or float
    :param dataframe: A pandas dataframe read in from a spreadsheet
    :type dataframe: pandas.datafarame
    :param exact: Boolean proscribing an exact match to containing; default is to locate a string or value that holds
        the input containing
    :type exact: bool
    :param single: return only the first co-ordinate, use only if the string/contains your searching for is unique and
        you have high confidence in your data
    :type single: bool
    :return: A co-ordinate in the form of (row, column) or a list containing a set of co-ordinates [(row, column), ...]
    :rtype: tuple or list of tuples

    """

    percent_tolerance = 0.001
    coordinates = []
    for row_index, row in dataframe.iterrows():
        for column_index, value in row.items():
            if value is not pandas.NA:
                if exact:
                    if value == containing:
                        coordinates.append((row_index, column_index))
                elif (
                    not exact
                    and not isinstance(value, str)
                    and not isinstance(containing, str)
                ):
                    if numpy.isclose(value, containing, rtol=percent_tolerance):
                        coordinates.append((row_index, column_index))
                elif not exact and type(value) is str:
                    if str(containing) in value:
                        coordinates.append((row_index, column_index))
    if single and coordinates:
        return coordinates[0]
    else:
        return coordinates


def transform_row_to_dict(
    row: typing.Union[int, str, pandas.Series], dataframe: pandas.DataFrame = None
) -> dict:
    """
    Parses a row of a dataframe (or a series from a dataframe) into a dictionary, special care is taken to transform
    array like data contained in a single cell to a list of numbers or strings.
    :param row: either the row index as an integer or a pandas.Series object
    :type row: int, pandas.Series
    :param dataframe: Provided if only an int is given to this method, will be queried at the row by the given integer
    :type dataframe: pandas.DataFrame
    :return: a dictionary corresponding a row from a (most likely multi-subject input sheet) spreadsheet
    :rtype: dict
    """
    if type(row) is pandas.Series:
        row = row
    elif type(row) is str or type(row) is int and dataframe is not None:
        if type(row) is int:
            row = dataframe.iloc[row]
        else:
            row = dataframe.loc[row]

    transformed = {}
    for key, value in row.items():
        try:
            evaluated = ast.literal_eval(str(value))
            if type(evaluated) is tuple:
                evaluated = list(evaluated)
        except (SyntaxError, ValueError):
            evaluated = value
        transformed[key] = evaluated

    return transformed


# noinspection PyPep8Naming
def get_recon_method(ReconstructionMethodString: str) -> dict:
    """
    Given the reconstruction method from a dicom header this function does its best to determine the name of the
    reconstruction, the number of iterations used in the reconstruction, and the number of subsets in the
    reconstruction.

    :param ReconstructionMethodString:
    :return: dictionary containing PET BIDS fields ReconMethodName, ReconMethodParameterUnits,
        ReconMethodParameterLabels, and ReconMethodParameterValues

    """
    contents = ReconstructionMethodString.replace(" ", "")
    subsets = None
    iterations = None

    # determine order of recon iterations and subsets, this is not  a surefire way to determine this...
    iter_sub_combos = {
        "iter_first": [
            r"\d\di\ds",
            r"\d\di\d\ds",
            r"\di\ds",
            r"\di\d\ds",
            r"i\d\ds\d",
            r"i\d\ds\d\d",
            r"i\ds\d",
            r"i\ds\d\d",
        ],
        "sub_first": [
            r"\d\ds\di",
            r"\d\ds\d\di",
            r"\ds\di",
            r"\ds\d\di",
            r"s\d\di\d",
            r"s\d\di\d\d",
            r"s\di\d",
            r"s\di\d\d",
        ],
    }

    iter_sub_combos["iter_first"] = [
        re.compile(regex) for regex in iter_sub_combos["iter_first"]
    ]
    iter_sub_combos["sub_first"] = [
        re.compile(regex) for regex in iter_sub_combos["sub_first"]
    ]
    order = None
    possible_iter_sub_strings = []
    iteration_subset_string = None
    # run through possible combinations of iteration substitution strings in iter_sub_combos
    for key, value in iter_sub_combos.items():
        for expression in value:
            iteration_subset_string = expression.search(contents)
            if iteration_subset_string:
                order = key
                iteration_subset_string = iteration_subset_string[0]
                possible_iter_sub_strings.append(iteration_subset_string)
    # if matches get ready to pick one
    if possible_iter_sub_strings:
        # sorting matches by string length as our method can return more than one match e.g. 3i21s will return
        # 3i21s and 3i1s or something similar
        possible_iter_sub_strings.sort(key=len)
        # picking the longest match as it's most likely the correct one
        iteration_subset_string = possible_iter_sub_strings[-1]

    # after we've captured the subsets and iterations we next need to separate them out from each other
    if iteration_subset_string and order:
        #  remove all chars replace with spaces
        just_digits = re.sub(r"[a-zA-Z]", " ", iteration_subset_string)
        just_digits = just_digits.strip()
        # split up subsets and iterations
        just_digits = just_digits.split(" ")
        # assign digits to either subsets or iterations based on order information obtained earlier
        if order == "iter_first" and len(just_digits) == 2:
            iterations = int(just_digits[0])
            subsets = int(just_digits[1])
        elif len(just_digits) == 2:
            iterations = int(just_digits[1])
            subsets = int(just_digits[0])
        else:
            # if we don't have both we decide that we don't have either, flawed but works for the samples in
            # test_dcm2niix4pet.py may. Will be updated when non-conforming data is obtained
            pass  # do nothing, this case shouldn't fire.....

    if iteration_subset_string:
        ReconMethodName = re.sub(iteration_subset_string, "", contents)
    else:
        ReconMethodName = contents

    # cleaning up weird chars at end or start of name
    ReconMethodName = re.sub(r"[^a-zA-Z0-9]$", "", ReconMethodName)
    ReconMethodName = re.sub(r"^[^a-zA-Z0-9]", "", ReconMethodName)

    expanded_name = ""
    # get the dimension as it's often somewhere in the name
    dimension = ""

    search_criteria = r"[1-4][D-d]"
    if re.search(search_criteria, ReconMethodName):
        dimension = re.search(search_criteria, ReconMethodName)[0]

    # doing some more manipulation of the recon method name to expand it from not so helpful acronyms
    possible_names = load_pet_bids_requirements_json(pet_reconstruction_metadata_json)[
        "reconstruction_names"
    ]

    # we want to sort the possible names by longest first that we don't break up an acronym prematurely
    sorted_df = pandas.DataFrame(possible_names).sort_values(
        by="value", key=lambda x: x.str.len(), ascending=False
    )

    possible_names = []
    for row in sorted_df.iterrows():
        possible_names.append({"value": row[1]["value"], "name": row[1]["name"]})

    for name in possible_names:
        if name["value"] in ReconMethodName:
            expanded_name += name["name"] + " "
            ReconMethodName = re.sub(name["value"], "", ReconMethodName)

    if expanded_name != "":
        ReconMethodName = dimension + " " * len(dimension) + expanded_name.rstrip()
        ReconMethodName = " ".join(ReconMethodName.split())

    if ReconMethodName in ["Filtered Back Projection", "3D Reprojection"]:
        ReconMethodParameterLabels = []
        ReconMethodParameterUnits = []
        ReconMethodParameterValues = []
    else:  # assume it is OSEM or a variant
        ReconMethodParameterLabels = ["subsets", "iterations"]
        ReconMethodParameterUnits = ["none", "none"]
        ReconMethodParameterValues = [subsets, iterations]

    reconstruction_dict = {
        "ReconMethodName": ReconMethodName,
        "ReconMethodParameterUnits": ReconMethodParameterUnits,
        "ReconMethodParameterLabels": ReconMethodParameterLabels,
        "ReconMethodParameterValues": ReconMethodParameterValues,
    }

    if None in reconstruction_dict["ReconMethodParameterValues"]:
        reconstruction_dict.pop("ReconMethodParameterValues")
        reconstruction_dict.pop("ReconMethodParameterUnits")
        for i in range(len(reconstruction_dict["ReconMethodParameterLabels"])):
            reconstruction_dict["ReconMethodParameterLabels"][i] = "none"

    return reconstruction_dict


def modify_config_file(var: str, value: Union[pathlib.Path, str], config_path=None):
    """
    Given a variable name and a value updates the config file with those inputs.
    Namely used (on Windows, but not limited to) to point to a dcm2niix executable (dcm2niix.exe)
    file as we don't assume dcm2niix is in the path.
    :param var: variable name
    :type var: str
    :param value: variable value, most often a path to another file
    :type value: Union[pathlib.Path, str]
    :param config_path: path to the config file, if not provided this function will look for a file at the user's home
    :type config_path: Union[pathlib.Path, str]
    :return: None
    :rtype: None
    """
    # load dcm2niix file
    if not config_path:
        config_file = pathlib.Path.home() / ".pet2bidsconfig"
    else:
        config_file = pathlib.Path(config_path)

    if config_file.exists():
        # open the file and read in all the lines
        temp_file = config_file.with_suffix(".temp")
        with open(config_file, "r") as infile, open(temp_file, "w") as outfile:
            updated_file = False
            for line in infile:
                if var + "=" in line:
                    outfile.write(f"{var}={value}\n")
                    updated_file = True
                else:
                    outfile.write(line)
            if not updated_file:
                outfile.write(f"{var}={value}\n")
        if system().lower() == "windows":
            config_file.unlink(missing_ok=True)
        temp_file.replace(config_file)
    else:
        # create the file
        try:
            with open(config_file, "w") as outfile:
                outfile.write(f"{var}={value}\n")
        except FileNotFoundError as err:
            logging.error(f"Unable to write to {config_file}\n{err}")


def check_units(entity_key: str, entity_value: str, accepted_units: Union[list, str]):
    """
    Given an entity's name, value, and an accepted range of values (accepted units), check whether those units are
    valid/in accepted units. Raises warning and returns False if units in entity value don't intersect with any entry
    in accepted_units

    :param entity_key: key/name of the entity
    :type entity_key: str
    :param entity_value: units value; some sort of SI unit(s) see (GBq, g, etc)
    :type entity_value: str
    :param accepted_units: a range of accepted units for the BIDS entity
    :type accepted_units: str or list
    :return: Whether the units in entity value ar allowed or not
    :rtype: bool
    """
    allowed = False
    for accepted in accepted_units:
        if entity_value.lower() == accepted.lower:
            allowed = True
            break

    if allowed:
        pass
    else:
        if type(accepted_units) is str or (
            type(accepted_units) is list and len(accepted_units) == 1
        ):
            warning = f"{entity_key} must have units as {accepted_units}, ignoring given units {entity_value}"
        elif type(accepted_units) is list and len(accepted_units) > 1:
            warning = f"{entity_key} must have units as on of  {accepted_units}, ignoring given units {entity_value}"

        logging.warning(warning)

    return allowed


def ad_hoc_checks(
    metadata: dict, modify_input=False, items_that_should_be_checked=None
):
    """
    Check to run on PET BIDS metadata to evaluate whether input is acceptable or not, this function will most likely be
    refactored to use the schema instead of relying on hardcoded checks as listed in items_that_should_be_checked
    :param metadata:
    :type metadata:
    :param modify_input:
    :type modify_input:
    :param items_that_should_be_checked: items to check, hardcoded at the moment, but can accept a dict as input
    :type items_that_should_be_checked: dict
    :return:
    :rtype:
    """
    # dictionary of entities and their acceptable units to check
    if items_that_should_be_checked is None:
        items_that_should_be_checked = {}
    hardcoded_items = {
        'InjectedRadioactivityUnits': ['MBq', 'mCi'],
        'SpecificRadioactivityUnits': ['Bq/g', 'MBq/ug'],
        'InjectedMassUnits': 'ug',
        'MolarActivityUnits': 'GBq/umolug',
        'MolecularWeightUnits': 'g/mol'
    }

    # if none are
    items_that_should_be_checked.update(**hardcoded_items)

    # iterate through ad hoc items_that_should_be_checked that exist in our metadata
    for entity, units in items_that_should_be_checked.items():
        check_input_entity = metadata.get(entity, None)
        if check_input_entity:
            # this will raise a warning if the units aren't acceptable
            units_are_good = check_units(
                entity_key=entity, entity_value=check_input_entity, accepted_units=units
            )

            # this will remove an entity from metadata form dictionary if it's not good
            if modify_input and not units_are_good:
                metadata.pop(entity)

    return metadata


def sanitize_bad_path(bad_path: Union[str, pathlib.Path]) -> Union[str, pathlib.Path]:
    if " " in str(bad_path):
        return f'"{bad_path}"'.rstrip().strip()
    else:
        return bad_path


def drop_row(dataframe: pandas.DataFrame, index: int):
    row = dataframe.loc[index]
    dataframe.drop(index, inplace=True)
    return row


def replace_nones(dictionary):
    json_string = json.dumps(dictionary)
    # sub nulls
    json_fixed = re.sub("null", '"none"', json_string)
    return json.loads(json_fixed)


def check_pet2bids_config(
    variable: str = "DCM2NIIX_PATH", config_path=Path.home() / ".pet2bidsconfig"
):
    """
    Checks the config file at users home /.pet2bidsconfig for the variable passed in,
    defaults to checking for DCM2NIIX_PATH. However, we can use it for anything we like,
    including setting paths to other useful files or "pet2bids" specific variables we'd like
    to access globally, or set as unchanging defaults.

    :param variable: a string variable name to check for in the config file
    :type variable: string
    :param config_path: path to the config file, defaults to $HOME/.pet2bidsconfig
    :type config_path: string or pathlib.Path
    :return: the value of the variable if it exists in the config file
    :rtype: str
    """
    log = logger("pypet2bids")
    # check to see if path to dcm2niix is in .env file
    dcm2niix_path = None
    variable_value = None
    pypet2bids_config = Path(config_path)
    if pypet2bids_config.exists():
        dotenv.load_dotenv(pypet2bids_config)
        variable_value = os.getenv(variable)
    # else we check our environment variables for the variable
    elif os.getenv(variable) and not pypet2bids_config.exists():
        variable_value = os.getenv(variable)
        log.warning(
            f"Found {variable} in environment variables as {variable_value}, but no .pet2bidsconfig file found at {pypet2bids_config}"
        )
    if variable == "DCM2NIIX_PATH":
        # check to see if dcm2niix is on the path at all
        check_on_path = subprocess.run(
            "dcm2niix -h",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if variable_value:
            # check dcm2niix path exists
            dcm2niix_path = Path(variable_value)
            check = subprocess.run(
                f"{dcm2niix_path} -h",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if check.returncode == 0:
                return dcm2niix_path
        elif (
            not variable_value
            and pypet2bids_config.exists()
            and check_on_path.returncode == 0
        ):
            # do nothing
            # log.info(
            #    f"DCM2NIIX_PATH not found in {pypet2bids_config}, but dcm2niix is on $PATH."
            # )
            return None
        else:
            log.error(
                f"Unable to locate dcm2niix executable at {dcm2niix_path.__str__()}"
                f" Set DCM2NIIX_PATH variable in {pypet2bids_config} or export DCM2NIIX_PATH=/path/to/dcm2niix into your environment variables."
            )
            return None
    if variable != "DCM2NIIX_PATH":
        return variable_value

    if not variable_value and not pypet2bids_config.exists():
        log.warning(
            f"Config file not found at {pypet2bids_config}, .pet2bidsconfig file must exist and "
            f"have variable: {variable} and {variable} must be set."
        )


class CustomFormatter(logging.Formatter):
    """
    Custom debugger courtesy of Sergey Pleshakov on stack overflow
    see https://stackoverflow.com/a/56944256
    """

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def hash_fields(**fields):
    hash_return_string = ""
    hash_string = ""
    if fields.get("ProtocolName", None):
        hash_return_string += f"{fields.get('ProtocolName')}_"
    keys_we_want = ["ses", "rec", "trc"]
    for key, value in fields.items():
        # sanitize values
        regex = r"[^a-zA-Z0-9]"
        value = re.sub(regex, "", str(value))
        hash_string += f"{value}_"
        if key in keys_we_want:
            hash_return_string += f"{value}_"

    hash_hex = hashlib.md5(hash_string.encode("utf-8")).hexdigest()

    return f"{hash_return_string}{hash_hex}"


def first_middle_last_frames_to_text(
    four_d_array_like_object, output_folder, step_name="_step_name_"
):
    frames = [
        0,
        four_d_array_like_object.shape[-1] // 2,
        four_d_array_like_object.shape[-1] - 1,
    ]
    frames_to_record = []
    for f in frames:
        frames_to_record.append(four_d_array_like_object[:, :, :, f])

    # now collect a single 2d slice from the "middle" of the 3d frames in frames_to_record
    for index, frame in enumerate(frames_to_record):
        numpy.savetxt(
            output_folder / f"{step_name}_frame_{frames[index]}.tsv",
            frames_to_record[index][:, :, frames_to_record[index].shape[2] // 2],
            delimiter="\t",
            fmt="%s",
        )
