# ActivitySim
# See full license in LICENSE.txt.

import os
import tempfile

import numpy as np
import orca
import pandas as pd
import pandas.util.testing as pdt
import pytest
import yaml
import openmatrix as omx

from .. import __init__
from ..tables import size_terms
from . import extensions

from ... import tracing
from ... import pipeline

# set the max households for all tests (this is to limit memory use on travis)
HOUSEHOLDS_SAMPLE_SIZE = 100
HH_ID = 961042

SKIP_FULL_RUN = False


def inject_settings(configs_dir, households_sample_size, chunk_size=None,
                    trace_hh_id=None, trace_od=None, check_for_variability=None):

    with open(os.path.join(configs_dir, 'settings.yaml')) as f:
        settings = yaml.load(f)
        settings['households_sample_size'] = households_sample_size
        if chunk_size is not None:
            settings['chunk_size'] = chunk_size
        if trace_hh_id is not None:
            settings['trace_hh_id'] = trace_hh_id
        if trace_od is not None:
            settings['trace_od'] = trace_od
        if check_for_variability is not None:
            settings['check_for_variability'] = check_for_variability

    orca.add_injectable("settings", settings)


def test_mini_pipeline_run():

    configs_dir = os.path.join(os.path.dirname(__file__), 'configs')
    orca.add_injectable("configs_dir", configs_dir)

    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    orca.add_injectable("output_dir", output_dir)

    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    orca.add_injectable("data_dir", data_dir)

    inject_settings(configs_dir, households_sample_size=HOUSEHOLDS_SAMPLE_SIZE)

    orca.clear_cache()

    # assert len(orca.get_table("households").index) == HOUSEHOLDS_SAMPLE_SIZE

    _MODELS = [
        'compute_accessibility',
        'school_location_simulate',
        'workplace_location_simulate',
        'auto_ownership_simulate'
    ]

    pipeline.run(models=_MODELS, resume_after=None)

    auto_choice = pipeline.get_table("households").auto_ownership

    # regression test: these are the 2nd-4th households in households table
    hh_ids = [2664549, 2122982, 1829334]
    choices = [0, 2, 1]
    expected_choice = pd.Series(choices, index=pd.Index(hh_ids, name="HHID"),
                                name='auto_ownership')

    print "auto_choice\n", auto_choice.head(4)
    pdt.assert_series_equal(auto_choice[hh_ids], expected_choice)

    pipeline.run_model('cdap_simulate')
    pipeline.run_model('mandatory_tour_frequency')

    mtf_choice = pipeline.get_table("persons").mandatory_tour_frequency

    per_ids = [24995, 92148, 92872]
    choices = ['work1', 'work_and_school', 'school2']
    expected_choice = pd.Series(choices, index=pd.Index(per_ids, name='PERID'),
                                name='mandatory_tour_frequency')

    print "mtf_choice\n", mtf_choice.head(20)
    pdt.assert_series_equal(mtf_choice[per_ids], expected_choice)

    pipeline.close()

    orca.clear_cache()


def test_mini_pipeline_run2():

    # the important thing here is that we should get
    # exactly the same results as for test_mini_pipeline_run
    # when we

    configs_dir = os.path.join(os.path.dirname(__file__), 'configs')
    orca.add_injectable("configs_dir", configs_dir)

    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    orca.add_injectable("output_dir", output_dir)

    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    orca.add_injectable("data_dir", data_dir)

    inject_settings(configs_dir, households_sample_size=HOUSEHOLDS_SAMPLE_SIZE)

    orca.clear_cache()

    # assert len(orca.get_table("households").index) == HOUSEHOLDS_SAMPLE_SIZE

    pipeline.start_pipeline('auto_ownership_simulate')

    auto_choice = pipeline.get_table("households").auto_ownership

    # regression test: these are the 2nd-4th households in households table
    hh_ids = [2664549, 2122982, 1829334]
    choices = [0, 2, 1]
    expected_auto_choice = pd.Series(choices, index=pd.Index(hh_ids, name="HHID"),
                                     name='auto_ownership')

    print "auto_choice\n", auto_choice.head(4)
    pdt.assert_series_equal(auto_choice[hh_ids], expected_auto_choice)

    pipeline.run_model('cdap_simulate')
    pipeline.run_model('mandatory_tour_frequency')

    mtf_choice = pipeline.get_table("persons").mandatory_tour_frequency

    per_ids = [24995, 92148, 92872]
    choices = ['work1', 'work_and_school', 'school2']
    expected_choice = pd.Series(choices, index=pd.Index(per_ids, name='PERID'),
                                name='mandatory_tour_frequency')

    print "mtf_choice\n", mtf_choice.head(20)
    pdt.assert_series_equal(mtf_choice[per_ids], expected_choice)

    pipeline.close()

    orca.clear_cache()


def full_run(resume_after=None, chunk_size=0,
             households_sample_size=HOUSEHOLDS_SAMPLE_SIZE,
             trace_hh_id=None, trace_od=None, check_for_variability=None):

    configs_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'example', 'configs')
    orca.add_injectable("configs_dir", configs_dir)

    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    orca.add_injectable("data_dir", data_dir)

    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    orca.add_injectable("output_dir", output_dir)

    inject_settings(configs_dir,
                    households_sample_size=households_sample_size,
                    chunk_size=chunk_size,
                    trace_hh_id=trace_hh_id,
                    trace_od=trace_od,
                    check_for_variability=check_for_variability)

    orca.clear_cache()

    tracing.config_logger()

    assert len(orca.get_table("households").index) == households_sample_size
    assert orca.get_injectable("chunk_size") == chunk_size

    _MODELS = [
        'compute_accessibility',
        'school_location_simulate',
        'workplace_location_simulate',
        'auto_ownership_simulate',
        'cdap_simulate',
        'mandatory_tour_frequency',
        'mandatory_scheduling',
        'non_mandatory_tour_frequency',
        'destination_choice',
        'non_mandatory_scheduling',
        'tour_mode_choice_simulate',
        'trip_mode_choice_simulate'
    ]

    pipeline.run(models=_MODELS, resume_after=resume_after)

    tours = pipeline.get_table('tours')
    tour_count = len(tours.index)

    pipeline.close()

    orca.clear_cache()

    return tour_count


def get_trace_csv(file_name):

    output_dir = os.path.join(os.path.dirname(__file__), 'output')

    df = pd.read_csv(os.path.join(output_dir, file_name))

    #        label    value_1    value_2    value_3    value_4
    # 0    tour_id        209         40         41         42
    # 1       mode  DRIVE_COM  DRIVE_LOC  DRIVE_LOC  DRIVE_LOC
    # 2  person_id    1888696    1888694    1888695    1888696
    # 3  tour_type     social       work       work     school
    # 4   tour_num          1          1          1          1

    # transpose df and rename columns
    labels = df.label.values
    df = df.transpose()[1:]
    df.columns = labels

    return df


def test_full_run():

    if SKIP_FULL_RUN:
        return

    tour_count = full_run(trace_hh_id=HH_ID, check_for_variability=True,
                          households_sample_size=HOUSEHOLDS_SAMPLE_SIZE)

    assert(tour_count == 231)

    mode_df = get_trace_csv('tour_mode_choice.mode.csv')
    mode_df.sort_values(by=['person_id', 'tour_type', 'tour_num'], inplace=True)

    print mode_df
    #         tour_id       mode person_id tour_type tour_num
    # value_2      40  DRIVE_LOC   1888694      work        1
    # value_3      41  DRIVE_LOC   1888695      work        1
    # value_4      42  DRIVE_LOC   1888696    school        1
    # value_1     209  DRIVE_COM   1888696    social        1

    assert (mode_df.person_id.values == ['1888694', '1888695', '1888696', '1888696']).all()
    assert (mode_df.tour_type.values == ['work', 'work', 'school', 'social']).all()
    assert (mode_df['mode'].values == ['DRIVE_LOC', 'DRIVE_LOC', 'DRIVE_LOC', 'DRIVE_COM']).all()


def test_full_run_with_chunks():

    # should get the same result with different chunk size

    if SKIP_FULL_RUN:
        return

    tour_count = full_run(trace_hh_id=HH_ID, check_for_variability=True,
                          households_sample_size=HOUSEHOLDS_SAMPLE_SIZE,
                          chunk_size=10)

    assert(tour_count == 231)

    mode_df = get_trace_csv('tour_mode_choice.mode.csv')
    mode_df.sort_values(by=['person_id', 'tour_type', 'tour_num'], inplace=True)

    assert (mode_df.person_id.values == ['1888694', '1888695', '1888696', '1888696']).all()
    assert (mode_df.tour_type.values == ['work', 'work', 'school', 'social']).all()
    assert (mode_df['mode'].values == ['DRIVE_LOC', 'DRIVE_LOC', 'DRIVE_LOC', 'DRIVE_COM']).all()


def test_full_run_stability():

    # hh should get the same result with different sample size

    if SKIP_FULL_RUN:
        return

    tour_count = full_run(trace_hh_id=HH_ID, check_for_variability=True,
                          households_sample_size=HOUSEHOLDS_SAMPLE_SIZE+1)

    mode_df = get_trace_csv('tour_mode_choice.mode.csv')
    mode_df.sort_values(by=['person_id', 'tour_type', 'tour_num'], inplace=True)

    print mode_df

    assert (mode_df.person_id.values == ['1888694', '1888695', '1888696', '1888696']).all()
    assert (mode_df.tour_type.values == ['work', 'work', 'school', 'social']).all()
    assert (mode_df['mode'].values == ['DRIVE_LOC', 'DRIVE_LOC', 'DRIVE_LOC', 'DRIVE_COM']).all()
