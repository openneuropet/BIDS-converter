"""
This module converts PMOD blood files (extension .bld) into BIDS compliant tsv and json files. It contains a class
PmodToBlood and a cli that uses that class to interface with the user. This module currently exists solely to convert
PMOD blood files and is not incorporated within any of the other conversion tools in PET2BIDS.

The command line arguments are details below, for more information about how this module works see the documentation for
PmodToBlood.

| *Authors: Anthony Galassi*
| *Copyright: OpenNeuroPET team*
"""

import json
import logging
import textwrap

import numpy
import pandas
import pandas as pd
import argparse
import warnings
import re
import ast
from pathlib import Path
from os.path import join

# from pypet2bids.helper_functions import ParseKwargs, collect_bids_part, open_meta_data

try:
    import helper_functions
except ModuleNotFoundError:
    import pypet2bids.helper_functions as helper_functions

epilog = textwrap.dedent('''
    
    example usage:
    
    convert-pmod-to-blood --whole-blood-path wholeblood.bld --parent-fraction parentfraction.bld # simplest use case
    convert-pmod-to-blood --whole-blood-path wholeblood.bld --parent-fraction parentfraction.bld --plasma-activity-path plasma.bld
    convert-pmod-to-blood --whole blood-path wholeblood.bld --parent-fraction parentfraction.bld --outputh-path sub-01/pet
    
    For more extensive examples rerun this program with the --show-example flag
''')

example1 = textwrap.dedent('''
Usage examples are below that verbosely describe and show the input consumed an the output generated by this program.
Additonal arguments/fields are passed via the kwargs flag in key value pairs.

Note: lines prepended with # denote comments/notes where as lines without # denote data or input arguments

example 1 (passing the bare minimum):
    
    # running the following
    convert-pmod-to-blood -whole whole_blood.bld -parent plasma_parent.bld
    # will result in outputting a tsv like the following:
    
    time	whole_blood_radioactivity	metabolite_parent_fraction
    25.2	0.000885	0.000874
    43.2	0.0192	0.00603
    51	0.92	1.38
    63	18.34858412	26.44553306
    90	51.96910035	73.40036984
    109.2	59.02807247	83.01412114
    130.8	74.9568219	106.0071338
    148.2	88.02307965	124.3830225
    171	86.93918061	120.924026
    189	47.18244008	65.42298506
    214.8	28.06571066	38.95386252
    319.2	10.22288119	14.11052535
    613.8	6.586049482	7.581724865
    919.2	7.448797008	5.784621668
    1810.2	6.49534108	4.294965789
    2719.2	5.373595253	2.836715768
    3607.2	4.798934663	2.48197381
    5419.8	3.898890497	2.05348682
    7207.2	3.772252717	1.77176473
    
    # and a json data dictionary as well
    {
      "WholeBloodAvail": "true",
      "MetaboliteAvail": "true",
      "time": {
        "Description": "Time in relation to time zero defined by the _pet.json",
        "Units": "s"
      },
      "whole_blood_radioactivity": {
        "Description": "Radioactivity in whole blood samples. Measured using COBRA counter.",
        "Units": "kBq/mL"
      },
      "metabolite_parent_fraction": {
        "Description": "Parent fraction of the radiotracer",
        "Units": "arbitrary"
      }
    }

 
''')


def cli():
    """
    Command line interface used to collect arguments for PmodToBlood class, note parameters defined below apply to the
    invocation at the command line **not** the method cli itself which takes no argument in Python.

    :param whole-blood-path: path to a PMOD .bld file containing the whole blood activity of a subject/run/scan
    :param parent-fraction-path: path to a PMOD .bld file containing the parent fraction of a subject/run/scan
    :param plasma-activity-path: path to a PMOD .bld file containing the plasma activity of a subject/run/scan
    :param output-path: the desired output path for the converted tsv and json files, if the path contains BIDS subject id's
        and session id's these will be extracted from the path and inserted into the filenames of the resultant tsv and json
        files.
    :param json: create a json sidecar/data-dictionary file along with output tsv's, default is set to True
    :param engine: engine used to read excel files, ignore this option as it will most likely be deprecated in the future
    :param kwargs: additional key pair arguments one wishes to include, such as extra entries for plasma or blood PET BIDS
        fields that aren't in PMOD blood files
    :param show-examples: shows an example of how to run this module as well as the outputs
    :return: collected arguments
    :rtype: argparse.namespace

    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--whole-blood-path",
        '-w',
        help="Path to pmod whole blood file.",
        required=False,
        type=Path
    )
    parser.add_argument(
        "--parent-fraction-path",
        "-f",
        help="Path to pmod parent fraction path.",
        required=False,
        type=Path
    )
    parser.add_argument(
        "--plasma-activity-path",
        "-p", help="Path to pmod plasma file.",
        required=False,
        type=Path,
        default=None
    )
    parser.add_argument(
        "--output-path",
        "-o",
        help="""Output path for output files (tsv and json) provide an existing folder path, if the output path is a
         BIDS path containing subject id and session id those values will be extracted an used to name the output 
         files.""",
        type=Path,
        default=None
    )
    parser.add_argument(
        "--json",
        "-j",
        help="Output a json data dictionary along with tsv files (default True)",
        default=True,
        type=bool
    )
    parser.add_argument(
        "--engine",
        "-e",
        help="Engine for loading PMOD files, see options for pandas.read_excel. Defaults to None.",
        default='',
        type=str
    )
    parser.add_argument(
        '--kwargs',
        '-k',
        nargs='*',
        action=helper_functions.ParseKwargs,
        help="Pass additional arguments not enumerated in this help menu, see documentation online" +
             " for more details.",
        default={}
    )
    parser.add_argument(
        '--show-examples',
        help="Show additional examples (verbose) of how to use this interface.",
        action='store_true'
    )

    args = parser.parse_args()

    return args


def type_cast_cli_input(kwarg_arg):
    """
    This method sanitizes collects inputs from the cli and casts them as native python data types.

    :param kwarg_arg: a kwarg argument parsed from the command line, literal string
    :type kwarg_arg: str
    :return: kwarg argument evaluated to python datatype
    :rtype: dict, list, str, int, float, bool
    """
    try:
        var = ast.literal_eval(kwarg_arg)
        if type(var) in [dict, list, str, int, float, bool]:
            return var
    except (ValueError, SyntaxError):
        # try truthy evals if the input doesn't evalute as a python type listed in the try statement
        if kwarg_arg.lower() in ['true', 't', 'yes']:
            return True
        elif kwarg_arg.lower() in ['false', 'f', 'no']:
            return False
        else:
            return kwarg_arg


class PmodToBlood:
    """
    Converts PMOD blood files to PET BIDS compliant tsv's and json _blood.* files

    :param whole_blood_activity: path to a PMOD whole blood activity file
    :type whole_blood_activity: pathlib.Path
    :param parent_fraction: path to a PMOD metabolite parent blood file
    :type parent_fraction: pathlib.Path
    :param output_path: path to write output tsv and jsons to, defaults to parent folder of whole blood input file
    :type output_path: pathlib.Path
    :param output_json: boolean specifying whether to output a json sidecar for the blood files, default is false
    :type output_json: bool
    :param engine: soon to be deprecated, determines what engine is used in pandas.read_excel
    :type engine: str
    :param kwargs: additional plasma/blood/radioactivity key/pair BIDS arguments, not required but if provided used during
        logic phase and written to sidecar json
    :type kwargs: dict
    """

    def __init__(
            self,
            whole_blood_activity: Path,
            parent_fraction: Path = Path(),
            plasma_activity: Path = Path(),
            output_path: Path = None,
            output_json: bool = False,
            engine='',
            **kwargs):

        if kwargs:
            try:
                self.kwargs = kwargs['kwargs']
            except KeyError:
                self.kwargs = kwargs
        else:
            self.kwargs = {}

        # relative closeness when comparing dataframes/inputs, default is set below
        self.rtol = 0.01
        self.atol = 0.02

        # cast input from kwargs
        for key, value in self.kwargs.items():
            self.kwargs[key] = type_cast_cli_input(value)

        self.units = None
        self.engine = engine

        # if given an output name run with that, otherwise we construct a name from the parent path the .bld files were 
        # found at.
        if output_path:
            self.output_path = Path(output_path)
            if not self.output_path.is_dir():
                raise FileNotFoundError(f"The output_path {output_path} must be an existing directory.")
        else:
            self.output_path = Path(whole_blood_activity).parent

        # check the output name for subject and session id
        if helper_functions.collect_bids_part('sub', str(self.output_path)):
            self.subject_id = helper_functions.collect_bids_part('sub', self.output_path)
        else:
            print("Subject id not found in output_path, checking key pair input.")
            self.subject_id = self.kwargs.get('subject_id', '')

        if helper_functions.collect_bids_part('ses', str(self.output_path)):
            self.session_id = helper_functions.collect_bids_part('ses', self.output_path)
        else:
            print("Session id not found in output_path, checking key pair input.")
            self.session_id = self.kwargs.get('session_id', '')

        self.output_json = output_json

        self.auto_sampled = []
        self.manually_sampled = []
        self.blood_series = {}
        self.duplicates = {}  # list of times that are duplicated across manual and automatic samples

        if whole_blood_activity.is_file():
            self.blood_series['whole_blood_activity'] = self.load_pmod_file(whole_blood_activity, engine=self.engine)

        if parent_fraction.is_file():
            self.blood_series['parent_fraction'] = self.load_pmod_file(parent_fraction, engine=self.engine)

        self.multiply_plasma = False
        # plasma activity is not required, but is used if provided
        if plasma_activity.is_file():
            self.blood_series['plasma_activity'] = self.load_pmod_file(plasma_activity, engine=self.engine)
            if 'whole' in str.lower(plasma_activity.name) and 'ratio' in str.lower(plasma_activity.name):
                self.multiply_plasma = True

        # one may encounter data collected manually and/or automatically, we vary our logic depending on the case
        self.data_collection = {}

        for blood_sample in self.blood_series.keys():
            var = f"{blood_sample}_collection_method"
            if not kwargs.get(var, None):
                self.ask_recording_type(blood_sample)
            else:
                self.data_collection[blood_sample] = kwargs.get(var)

        for measure, collection_method in self.data_collection.items():
            if collection_method == 'manual':
                self.manually_sampled.append({'name': measure})
            if collection_method == 'automatic':
                self.auto_sampled.append({'name': measure})

        # scale time to seconds rename columns
        self.scale_time_rename_columns()

        # check blood files for consistency
        self.check_time_info()

        # warn if plasma data may be interpolated
        self.check_for_interpolated_data()

        # remove duplicates from automatically sampled data, this data will then be written out to manual versions
        # of each recording
        #self.deduplicate()

        self.write_out_tsvs()

        if self.output_json:
            self.write_out_jsons()

    @staticmethod
    def load_pmod_file(pmod_blood_file: Path, engine=''):
        """
        Loads a pmod .bld blood file in with pandas.

        :param pmod_blood_file: path to pmod blood file
        :type pmod_blood_file: pathlib.Path
        :param engine: python engine used to read excel sheet with pandas.read_excel,
        :type engine: str
        :return: contents of .bld file
        :rtype: pandas.DataFrame
        """
        if pmod_blood_file.is_file() and pmod_blood_file.exists():
            loaded_file = helper_functions.open_meta_data(pmod_blood_file)
            # drop unnamed columns
            loaded_file = loaded_file.loc[:, ~loaded_file.columns.str.contains('^Unnamed')]
            return loaded_file
        else:
            raise FileNotFoundError(str(pmod_blood_file))

    def check_time_info(self):
        """
        Checks for time units, and time information between .bld files, number of rows and the values
        in the time index must be the same across each input .bld file. Additionally, renames time column
        to 'time' instead of what it's defined as in the pmod file. Does some more checks and scaling of plasma data,
        de-duplication etc.
        """
        # if there is only a single input do nothing, else go through each file. This shouldn't get reached
        # as whole_blood_activity and plasma_activity are required
        if len(self.blood_series) >= 2 and len(set(self.data_collection.values())) == 1:
            row_lengths = {}
            for key, bld_data in self.blood_series.items():
                row_lengths[key] = len(bld_data)

            if len(set(row_lengths.values())) > 1:
                err_message = f"Sampling method for all PMOD blood files (.bld) given as " \
                              f"{list(set(self.data_collection.values()))[0]} must be of the same dimensions" \
                              f" row-wise!\n"
                for key, value in row_lengths.items():
                    err_message += f"{key} file has {value} rows\n"

                err_message += "Check input files are valid."

                raise Exception(err_message)

            # lastly make sure the same time points exist across each input file/dataframe
            whole_blood_activity = self.blood_series.pop('whole_blood_activity')
            for key, dataframe in self.blood_series.items():
                try:
                    assert whole_blood_activity['time'].equals(dataframe['time'])
                except AssertionError:
                    raise AssertionError(f"Time(s) must have same values between input files, check time columns.")
            # if it all checks out put the whole blood activity back into our blood series object
            self.blood_series['whole_blood_activity'] = whole_blood_activity

        # checks to make sure that an auto-sampled file has more entries in it than a manually sampled file,
        # John Henry must lose.
        elif len(self.blood_series) >= 2 and len(set(self.data_collection.values())) > 1:
            # check to make sure auto sampled .bld files have more entries than none autosampled
            compare_lengths = []
            for key, sampling_type in self.data_collection.items():
                compare_lengths.append(
                    {'name': key, 'sampling_type': sampling_type, 'sample_length': len(self.blood_series[key])})

            auto_sampled, manually_sampled = [], []
            for each in compare_lengths:
                if 'auto' in str.lower(each['sampling_type']):
                    auto_sampled.append(each)
                elif 'manual' in str.lower(each['sampling_type']):
                    manually_sampled.append(each)

            for auto in auto_sampled:
                for manual in manually_sampled:
                    if auto['sample_length'] < manual['sample_length']:
                        logging.warning(
                            f"Autosampled .bld input for {auto['name']} has {auto['sample_length']} rows"
                            f" and Manually sampled input has {manual['sample_length']} rows. Autosampled blood "
                            f"files should have more rows than manually sampled input files. Check .bld inputs.")

            # we want to make sure that in the case of mixed data we don't include manual time points in the autosampled
            # curves, first we find duplicates.

            whole_blood_activity = self.blood_series.get('whole_blood_activity', pandas.DataFrame())
            plasma_activity = self.blood_series.get('plasma_activity', pandas.DataFrame())
            parent_fraction = self.blood_series.get('parent_fraction', pandas.DataFrame())
            duplicates = {}

            # wp is short for whole blood and plasma activity, we're just using wp to make our conditional statements
            # look a bit cleaner while retaining the namespace from which activity series come from. Hanging onto these
            # names in this dictionary makes creating manual files later during de-duplication
            wp = {
                    'whole_blood_activity': whole_blood_activity,
                    'plasma_activity': plasma_activity
                    }

            # case 1 whole blood time == plasma time && parent fraction time exists
            if len(wp['whole_blood_activity']) == len(wp['plasma_activity']) and parent_fraction:
                # get ready for duplicates
                for key in wp.keys():
                    if self.data_collection.get(key) == 'automatic':
                        duplicates[key] = []

                for activity_series in duplicates.keys():
                    for pf_time in parent_fraction.get('time', []):
                        for activity_time in wp.get(key).get('time', []):
                            if numpy.isclose(pf_time, activity_time, atol=self.atol):
                                duplicates[activity_series].append(activity_time)

            # case 2 whole blood time > plasma time && parent fraction time exists
            elif len(wp['whole_blood_activity']) > len(wp['plasma_activity']) and parent_fraction is not None:
                # get ready for duplicates
                for key in wp.keys():
                    if self.data_collection.get(key) == 'automatic':
                        duplicates[key] = []


                if len(wp['plasma_activity']) == (len(parent_fraction) - 1):
                    if parent_fraction['time'][0] == wp['whole_blood_activity']['time'][0] and parent_fraction['time'][0] == 0:
                        if self.multiply_plasma:
                            wp['plasma_activity'].loc[-1] = [0, 1]
                        else:
                            wp['plasma_activity'].loc[-1] = [0, 0]

                        wp['plasma_activity'].index = wp['plasma_activity'].index + 1
                        wp['plasma_activity'] = wp['plasma_activity'].sort_values('time').reset_index(drop=True)
                        self.blood_series['plasma_activity'] = wp['plasma_activity']
                    else:
                        raise Exception(f"Parent fraction and plasma times do not match, we cannot figure out which "
                                        f"time points to extract in whole blood.")

                for activity_series in duplicates.keys():
                    for pf_time in parent_fraction.get('time', []):
                        for df_time in wp.get(key).get('time', []):
                            if numpy.isclose(pf_time, df_time, atol=self.atol):
                                duplicates[activity_series].append(df_time)

            # end else w/ no duplicates
            else:
                pass

            # catch only unique duplicates
            for k, v in duplicates.items():
                if v != []:
                    self.duplicates[k] = v

            # now we go ahead and remove any duplicates that exist in existing blood data
            for activity_series, duplicate_times in self.duplicates.items():
                # for name, sample_type in self.data_collection.items():
                #     if activity_series == name and sample_type == 'automatic':
                #         series_is_auto_sampled = True
                #     else:
                #         series_is_auto_sampled = False

                # we only want to remove rows if they exist in autosampled data, but are clearly manually sampled
                if self.data_collection.get(activity_series) == 'automatic':
                    removed_rows = pandas.DataFrame(
                        columns=self.blood_series.get(activity_series, pandas.DataFrame()).columns)

                    for time in duplicate_times:
                        index = helper_functions.get_coordinates_containing(time, self.blood_series[activity_series],
                                                                            exact=False)

                        if index:
                            row = index[0][0]

                            dropped_row = helper_functions.drop_row(self.blood_series[activity_series], row)

                            # using the loc indexer, append the series to the end of the df
                            removed_rows.loc[len(removed_rows)] = dropped_row

                # update the blood series object with the popped/dropped row
                new_string = f"{activity_series}_manually_popped"
                self.blood_series[new_string] = removed_rows.sort_values('time').reset_index(drop=True)
                self.manually_sampled.append({'name': new_string})
                self.data_collection[new_string] = 'manual'

                if len(self.blood_series[new_string]) == (len(parent_fraction) - 1):
                    if (self.blood_series['parent_fraction']['time'][0] != self.blood_series[new_string]['time'][0]
                            and parent_fraction['time'][0] == 0):

                        self.blood_series[new_string].loc[-1] = [0, 0]
                        self.blood_series[new_string].index = self.blood_series[new_string].index + 1
                        self.blood_series[new_string] = self.blood_series[new_string].sort_values('time').reset_index(drop=True)

                    else:
                        raise Exception(f"Parent fraction and plasma times do not match, we cannot figure out which "
                                        f"time points to extract in whole blood.")

        # if provided with the plasma ratio we multiply the whole blood by it, math time
        if self.multiply_plasma:
            # get our plasma activity, we get the manually popped if it exists
            pa = self.blood_series.get(
                'plasma_activity_manually_popped',
                self.blood_series['plasma_activity'])

            if self.blood_series.get('whole_blood_activity_manually_popped', pandas.DataFrame()).shape[0] != 0:

                wba = self.blood_series['whole_blood_activity_manually_popped']
                new_plasma = wba['whole_blood_radioactivity'] * self.blood_series['plasma_activity']['plasma_radioactivity']

                temp = pandas.DataFrame({'time': self.blood_series['plasma_activity']['time'],
                                         'plasma_radioactivity': new_plasma})

                self.blood_series['plasma_activity'] = temp

            else:
                self.blood_series['plasma_activity'] = self.blood_series['plasma_activity'] * self.blood_series['whole_blood']


    def scale_time_rename_columns(self):
        """
        Scales time info if it's not in seconds and renames dataframe column to 'time' instead of given column name in 
        .bld file. Renames radioactivity column to BIDS compliant column name if it's in units Bq/cc or  Bq/mL.
        """
        # scale time info to seconds if it's minutes
        for name, dataframe in self.blood_series.items():
            time_column_header_name = []
            radioactivity_column_header_name = []
            parent_fraction_column_header_name = []
            time_scalar = 1.0
            time_column_header_name = [header for header in list(dataframe.columns) if 'sec' in str.lower(header)]
            if not time_column_header_name:
                time_column_header_name = [header for header in list(dataframe.columns) if 'min' in str.lower(header)]
                if time_column_header_name:
                    time_scalar = 60.0

            if time_column_header_name and len(time_column_header_name) == 1:
                dataframe.rename(columns={time_column_header_name[0]: 'time'}, inplace=True)
            else:
                raise Exception("Unable to locate time column in blood file, make sure input files are formatted "
                                "to include a single time column in minutes or seconds.")

            # scale the time column to seconds
            dataframe['time'] = dataframe['time'] * time_scalar
            self.blood_series[name] = dataframe

            # locate parent fraction column
            parent_fraction_column_header_name = [header for header in dataframe.columns if
                                                  'parent' in str.lower(header)]
            parent_fraction_is_suspicous = False
            if len(parent_fraction_column_header_name) >= 1:
                pf = str(parent_fraction_column_header_name[0]).lower()
                if 'bq' in pf or 'ml' in pf:
                    logging.warning(f"Found {parent_fraction_column_header_name[0]} in {name} input file, this column "
                                    f"must be unitless")
                    parent_fraction_is_suspicous = True

            if not parent_fraction_column_header_name or parent_fraction_is_suspicous:
                # locate radioactivity column
                radioactivity_column_header_name = [header for header in dataframe.columns if
                                                    'bq' and 'cc' in str.lower(header)]
                # run through radio updating conversion if not percent parent
            if radioactivity_column_header_name and len(time_column_header_name) == 1:
                sub_ml_for_cc = re.sub('cc', 'mL', radioactivity_column_header_name[0])
                extracted_units = re.search(r'\[(.*?)\]', sub_ml_for_cc)
                second_column_name = None
                if 'plasma' in str.lower(radioactivity_column_header_name[0]) or \
                        ('bq/cc' in str.lower(radioactivity_column_header_name[0]) and name == 'plasma_activity'):
                    second_column_name = 'plasma_radioactivity'

                if name == 'whole_blood_activity':
                    if 'whole' in str.lower(radioactivity_column_header_name[0]) or 'blood' in str.lower(
                            radioactivity_column_header_name[0]):
                        second_column_name = 'whole_blood_radioactivity'

                if second_column_name:
                    dataframe = dataframe.rename({radioactivity_column_header_name[0]: second_column_name},
                                                 axis='columns')

                if extracted_units:
                    self.units = extracted_units.group(1)
                else:
                    raise Exception(
                        "Unable to determine radioactivity entries from .bld column name. Column name/units must be in "
                        "Bq/cc or Bq/mL")
            # if percent parent rename column accordingly
            if parent_fraction_column_header_name and len(
                    parent_fraction_column_header_name) == 1 and name != 'plasma_activity':
                dataframe = dataframe.rename({parent_fraction_column_header_name[0]: 'metabolite_parent_fraction'},
                                             axis='columns')
            self.blood_series[name] = dataframe.copy(deep=True)

    def ask_recording_type(self, recording: str):
        """
        Prompt user about data collection to determine how data was collected for each
        measure. e.g. auto-sampled, manually drawn, or a combination of the two.

        :param recording: the name of the recording
        :type: str
        :return: None
        :rtype: None
        """
        how = None
        while how != 'a' or how != 'm':
            how = input(f"How was the {recording} data sampled?:\nEnter A for automatically or M for manually\n")
            if str.lower(how) == 'm':
                self.data_collection[recording] = 'manual'
                break
            elif str.lower(how) == 'a':
                self.data_collection[recording] = 'automatic'
                break
            elif str.lower(how) == 'y':
                self.data_collection[recording] = 'manual'
                warnings.warn(
                    f"Received {how} as input, assuming input recieved from cli w/ '-y' option on bash/zsh etc, "
                    f"defaulting to manual input")
                break
            else:
                print(f"You entered {how}; please enter either M or A to exit this prompt")

    def write_out_tsvs(self):
        """
        Writes out blood data to tsv files corresponding to autosampled or manually sampled versions (dependent on user
        input)

        :return: None
        :rtype: None
        """
        # first we combine the various blood datas into one or two dataframes, the autosampled data goes into a
        # recording_autosample, and the manually sampled data goes into a recording_manual if they exist
        if self.subject_id:
            file_path = join(self.output_path, self.subject_id + '_')
            if self.session_id:
                file_path += self.session_id + '_'
            manual_path = file_path + 'recording-manual_blood.tsv'
            automatic_path = file_path + 'recording-automatic_blood.tsv'
        else:
            manual_path = join(self.output_path, 'recording-manual_blood.tsv')
            automatic_path = join(self.output_path, 'recording-automatic_blood.tsv')

        # first combine autosampled data
        if self.auto_sampled:
            first_auto_sampled = self.blood_series[self.auto_sampled.pop()['name']]
            for remaining_auto in self.auto_sampled:
                remaining_auto = self.blood_series[remaining_auto['name']]
                column_difference = remaining_auto.columns.difference(first_auto_sampled.columns)
                for column in list(column_difference):
                    first_auto_sampled[column] = remaining_auto[column]
            first_auto_sampled.to_csv(automatic_path, sep='\t', index=False)

        # combine any additional manually sampled dataframes
        if self.manually_sampled:
            first_manually_sampled = self.blood_series[self.manually_sampled.pop()['name']]
            for remaining_manual in self.manually_sampled:
                remaining_manual = self.blood_series[remaining_manual['name']]
                column_difference = remaining_manual.columns.difference(first_manually_sampled.columns)
                for column in list(column_difference):
                    first_manually_sampled[column] = remaining_manual[column]
            first_manually_sampled.to_csv(manual_path, sep='\t', index=False)

    def write_out_jsons(self):
        """
        Writes out sidecar json to correspond to _blood.tsv files

        :return: None
        :rtype: None
        """
        if self.subject_id:
            file_path = join(self.output_path, self.subject_id + '_')
            if self.session_id:
                file_path += self.session_id + '_'
            file_path += 'blood.json'
        else:
            file_path = join(self.output_path, 'blood.json')

        side_car_template = {
            "Time": {
                "Description": "Time in relation to time zero defined by the _pet.json",
                "Units": "s"
            },
            "whole_blood_radioactivity": {
                "Description": 'Radioactivity in whole blood samples.',
                "Units": self.units
            },
            "metabolite_parent_fraction": {
                "Description": 'Parent fraction of the radiotracer',
                "Units": 'arbitrary'
            },
        }

        if self.kwargs.get('MetaboliteMethod', None):
            side_car_template['MetaboliteMethod'] = self.kwargs.get('MetaboliteMethod'),
        elif self.kwargs.get('MetaboliteRecoveryCorrectionApplied', None):
            side_car_template['MetaboliteRecoveryCorrectionApplied'] = self.kwargs.get(
                'MetaboliteRecoveryCorrectionApplied')
        elif self.kwargs.get('DispersionCorrected', None):
            side_car_template['DispersionCorrected'] = self.kwargs.get('DispersionCorrected')

        side_car_template['MetaboliteAvail'] = True

        if self.kwargs.get('MetaboliteMethod', None):
            side_car_template['MetaboliteMethod'] = self.kwargs.get('MetaboliteMethod')
        else:
            warnings.warn("Parent fraction is available, but MetaboliteMethod is not specified, which is not BIDS "
                          "compliant.")

        if self.kwargs.get('DispersionCorrected'):
            side_car_template['DispersionCorrected'] = self.kwargs.get('DispersionCorrected')
        else:
            warnings.warn('Parent fraction is available, but there is no information if DispersionCorrected was' +
                          'applied, which is not BIDS compliant')

        if self.blood_series.get('plasma_activity', None) is type(pd.DataFrame):
            side_car_template['PlasmaAvail'] = True
            side_car_template['plasma_radioactivity'] = {
                'Description': 'Radioactivity in plasma samples',
                'Units': self.units
            }

        with open(file_path, 'w') as out_json:
            json.dump(side_car_template, out_json, indent=4)

    def check_for_interpolated_data(self):
        # check to see if there may exist (emphasis on may) interpolated plasma values
        if type(self.blood_series.get('plasma_activity', None)) is not None:
            # extract parent fraction/metabolite fraction as series from dataframes
            metabolite_parent_fraction_series = pandas.Series(dtype='float64')
            for name, dataframe in self.blood_series.items():
                columns = dataframe.columns
                for entry in columns:
                    if 'parent' in str.lower(entry) or 'fraction' in str.lower(entry):
                        metabolite_parent_fraction_series = dataframe[str(entry)]
                        break
                if len(metabolite_parent_fraction_series) > 0:
                    break

            # check dataframes for plasma activity
            plasma_activity_series = pandas.Series(dtype='float64')
            for name, dataframe in self.blood_series.items():
                columns = dataframe.columns
                for entry in columns:
                    if 'plasma_radioactivity' in entry:
                        plasma_activity_series = dataframe[str(entry)]
                        break
                if len(plasma_activity_series) > 0:
                    break

            if len(plasma_activity_series) > 0 and len(metabolite_parent_fraction_series) > 0:
                if len(plasma_activity_series) == len(metabolite_parent_fraction_series):
                    logging.warning(f"plasma_activity_series and metabolite_parent_fraction have same "
                                    f"length {len(plasma_activity_series)}, plasma data may be interpolated, BIDS "
                                    f"prefers raw data.")

    def check_fraction_is_fraction(self):
        # collect parent fractions wherever they may exist
        fraction_series = []
        for name, dataframe in self.blood_series.items():
            for column in dataframe.columns:
                if 'fraction' in str(column).lower():
                    fraction_series.append({name: dataframe[column]})

        for fraction_column in fraction_series:
            for name, values in fraction_column.items():
                for value in values:
                    logging.warning(f"No, no my friend parent/metabolite fraction must be less than or equal to 1,"
                                    f" found {value} in {name}.")


def main():
    """
    Executes the PmodToBlood class using argparse

    :return: None
    """

    cli_args = cli()

    if cli_args.show_examples:
        print(example1)
    elif cli_args.whole_blood_path and cli_args.parent_fraction_path:
        pmod_to_blood = PmodToBlood(
            whole_blood_activity=cli_args.whole_blood_path,
            parent_fraction=cli_args.parent_fraction_path,
            plasma_activity=cli_args.plasma_activity_path,
            output_path=cli_args.output_path,
            output_json=cli_args.json,
            engine=cli_args.engine,
            kwargs=cli_args.kwargs
        )
    else:
        raise Exception(f"--whole-blood-path (-w) and --parent-fraction-path (-p) are both required!")


if __name__ == "__main__":
    main()
