import pandas as pd
import argparse
import warnings
import re
from pathlib import Path
from os.path import join

from pypet2bids.helper_functions import ParseKwargs

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--whole-blood-path",
        '-whole',
        help="Path to pmod whole blood file.",
        required=True,
        type=Path
    )
    parser.add_argument(
        "--parent-fraction-path",
        "-parent",
        help="Path to pmod parent fraction path.",
        required=True,
        type=Path
    )
    parser.add_argument(
        "--plasma-activity-path",
        "-plasma", help="Path to pmod plasma file.",
        required=False,
        type=Path,
        default=None
    )
    parser.add_argument(
        "--output-name", 
        "-o", 
        help="Name Stem for output files (tsv and json) provide as either folder path or filename path.",
        type=str,
        default=''
    )
    parser.add_argument(
        "--json", 
        "-j", 
        help="Output a json data dictionary along with tsv files (default True)",
        default=True,
        type=bool
    )
    parser.add_argument(
        '--kwargs', 
        '-k', 
        nargs='*',
        action=ParseKwargs,
        help="Pass additional arguments not enumerated in this help menu, see documentation online" +
        " for more details.",
        default={}
        )

    args = parser.parse_args()

    return args

class PmodToBlood:
    def __init__(
            self,
            whole_blood_activity: Path,
            parent_fraction: Path,
            plasma_activity: Path = None,
            blood_sampling_type: str = 'both',
            output_name: str = '',
            output_json: bool = False,
            **kwargs):
        
        self.auto_sampled = []
        self.manually_sampled = []

        # whole blood and parent fraction are required, always attempt to load
        self.blood_series = {'whole_blood_activity': self.load_pmod_file(whole_blood_activity),
                             'parent_fraction': self.load_pmod_file(parent_fraction)}

        # plasma activity is not required, but is used if provided
        if plasma_activity:
            self.blood_series['plasma_activity'] = self.load_pmod_file(plasma_activity)
        self.data_collection = {}


        # one may encounter data collected manually and/or automatically, we vary our logic depending on the case
        self.data_collection = {}

        for blood_sample in self.blood_series.keys():
            var = f"{blood_sample}_collection_method"
            if not kwargs.get(var, None):
                self.ask_recording_type(blood_sample)
            else:
                self.data_collection[blood_sample] = kwargs.get(var)
        
        # scale time to seconds rename columns
        self.scale_time_rename_columns()

        # check blood files for consistency
        self.check_time_info()

        # if given an output name run with that, otherwise we construct a name from the parent path the .bld files were 
        # found at.
        if output_name:
            self.output_name = Path(output_name)
        else:
            self.output_name = Path(whole_blood_activity).parent

        self.write_out_tsvs()

    @staticmethod
    def load_pmod_file(pmod_blood_file: Path):
        if pmod_blood_file.is_file() and pmod_blood_file.exists():
            loaded_file = pd.read_excel(str(pmod_blood_file))
            return loaded_file
        else:
            raise FileNotFoundError(str(pmod_blood_file))

    def check_time_info(self):
        """
        Checks for time units, and time information between .bld files, number of rows and the values
        in the time index must be the same across each input .bld file. Additionally, renames time column
        to 'time' instead of what it's defined as in the pmod file.
        """
        # if there is only a single input do nothing, else go through each file. This shouldn't get reached
        # as whole_blood_activity and plasma_activity are required
        if len(self.blood_series) >= 2 and len(set(self.data_collection.values())) ==1:
            row_lengths = {}
            for key, bld_data in self.blood_series.items():
                row_lengths[key] = len(bld_data)

            if len(set(row_lengths.values())) > 1:
                err_message = f"Sampling method for all PMOD blood files (.bld) given as " \
                              f"{list(set(self.data_collection.values()))[0]} must be of the same dimensions row-wise!\n"
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
        
        # checks to make sure that an autosampled file has more entries in it than a manually sampled file, John Henry must lose.
        elif len(self.blood_series) >= 2 and len(set(self.data_collection.values())) > 1:
            # check to make sure auto sampled .bld files have more entries than none autosampled
            compare_lengths = []
            for key, sampling_type in self.data_collection.items():
                compare_lengths.append({'name': key,'sampling_type': sampling_type, 'sample_length': len(self.blood_series[key])})

            for each in compare_lengths:
                if 'auto' in str.lower(each['sampling_type']):
                    self.auto_sampled.append(each)
                elif 'manual' in str.lower(each['sampling_type']):
                    self.manually_sampled.append(each)

            for auto in self.auto_sampled:
                for manual in self.manually_sampled:
                    if auto['sample_length'] < manual['sample_length']:
                        warnings.warn(
                            f"Autosampled .bld input for {list(auto.keys())[0]} has {len(auto['sample_length'])} rows\n\
                              and Manually sampled input has {len({manual['sample_length']})}. Autosampled blood files\n\
                              should have more rows than manually sampled input files. Check .bld inputs.")
        

    def scale_time_rename_columns(self):
        """
        Scales time info if it's not in seconds and renames dataframe column to 'time' instead of given column name in 
        .bld file. Renames radioactivity column to BIDS compliant column name if it's in units Bq/cc or  Bq/mL.
        """
        # scale time info to seconds if it's minutes
        time_scalar = 1.0
        for name, dataframe in self.blood_series.items():
            time_column_header_name = [header for header in dataframe.columns if 'sec' in str.lower(header)]
            if not time_column_header_name:
                time_column_header_name = [header for header in dataframe.columns if 'min' in str.lower(header)]
                time_scalar = 60.0

            if time_column_header_name and len(time_column_header_name) == 1:
                dataframe.rename(columns={time_column_header_name[0]: 'time'}, inplace=True)
            else:
                raise Exception("Unable to locate time column in blood file, make sure input files are formatted "
                                "to include a single time column in minutes or seconds.")

            # scale the time column to seconds
            dataframe['time'] = dataframe['time']*time_scalar
            self.blood_series[name] = dataframe

            # locate radioactivity column
            radioactivity_column_header_name = [header for header in dataframe.columns if 'bq' and 'cc' in str.lower(header)]
            # locate parent fraction column
            parent_fraction_column_header_name = [header for header in dataframe.columns if 'parent' in str.lower(header)]
            # run through radio updating conversion if not percent parent
            if radioactivity_column_header_name and len(time_column_header_name) == 1:
                sub_ml_for_cc =re.sub('cc', 'mL', radioactivity_column_header_name[0])
                extracted_units = re.search(r'\[(.*?)\]', sub_ml_for_cc)
                second_column_name = None
                if 'plasma' in str.lower(radioactivity_column_header_name[0]):
                    second_column_name = 'plasma_radioactivity'
                if 'whole' in str.lower(radioactivity_column_header_name[0]) or 'blood' in str.lower(radioactivity_column_header_name[0]):
                    second_column_name = 'whole_blood_radioactivity'
                
                if second_column_name:
                    dataframe.rename(columns={radioactivity_column_header_name[0]: second_column_name}, inplace=True)

                if extracted_units:
                    self.units = extracted_units.group(1)
                else:
                    raise Exception("Unable to determine radioactivity entries from .bld column name. Column name/units must be in Bq/cc or Bq/mL")
            # if percent parent rename column accordingly
            elif parent_fraction_column_header_name and len(parent_fraction_column_header_name) == 1:
                    dataframe.rename(columns={parent_fraction_column_header_name[0]: 'metabolite_parent_fraction'}, inplace=True)
            self.blood_series[name] == dataframe

    def ask_recording_type(self, recording: str):
        """
        Prompt user about data collection to determine how data was collected for each
        measure. e.g. auto-sampled, manually drawn, or a combination of the two
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
                warnings.warn(f"Recieved {how} as input, assuming input recieved from cli w/ '-y' option on bash/zsh etc, defaulting to manual input")
                break
            else:
                print(f"You entered {how}; please enter either M or A to exit this prompt")

    def write_out_tsvs(self, subject_id: str = '', session_id: str = ''):
        # first we combine the various blood datas into one or two dataframes, the autosampled data goes into a recording_autosample,
        # and the manually sampled data goes into a recording_manual if they exist
        file_name = ''
        if subject_id:
            file_name += 'sub-' + subject_id + '_'
        if session_id:
            file_name += 'ses-' + session_id + '_'

        if not self.output_name.is_file():
            file_name = join(self.output_name, file_name)
        else:
            file_name = self.output_name.stem

        manual_path = file_name + '_recording-manual_blood.tsv'
        automatic_path = file_name + '_recording-automatic_blood.tsv'

        # first combine autosampled data
        if self.auto_sampled:
            first_auto_sampled = self.auto_sampled.pop()
            for remaining_auto in self.auto_sampled:
                column_difference = remaining_auto.columns.difference(first_auto_sampled.columns)
                for column in list(column_difference):
                    first_auto_sampled[column] = remaining_auto[column]
            first_auto_sampled.to_csv(automatic_path, sep='\t', index=False)

        # combine any additional manually sampled dataframes
        if self.manually_sampled:
            first_manually_sampled = self.manually_sampled.pop()
            for remaining_manual in self.manually_sampled:
                column_difference = remaining_manual.columns.difference(first_manually_sampled.columns)
                for column in list(column_difference):
                    first_manually_sampled[column] = remaining_manual[column]
            first_manually_sampled.to_csv(manual_path, sep='\t', index=False)

def main():
    """
    Executes the PmodToBlood class using argparse

    :return: None
    """

    cli_args = cli()
    pmod_to_blood = PmodToBlood(
        whole_blood_activity=cli_args.whole_blood_path,
        parent_fraction=cli_args.parent_fraction_path,
        plasma_activity=cli_args.plasma_activity_path,
        output_name=cli_args.output_name,
        output_json=cli_args.json,
        kwargs=cli_args.kwargs
    )

if __name__ == "__main__":
    main()