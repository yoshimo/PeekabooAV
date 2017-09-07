###############################################################################
#                                                                             #
# Peekaboo Extended Email Attachment Behavior Observation Owl                 #
#                                                                             #
# processor.py                                                                  #
###############################################################################
#                                                                             #
# Copyright (C) 2016-2017  science + computing ag                             #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or (at       #
# your option) any later version.                                             #
#                                                                             #
# This program is distributed in the hope that it will be useful, but         #
# WITHOUT ANY WARRANTY; without even the implied warranty of                  #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU           #
# General Public License for more details.                                    #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################


import os
from shutil import copyfile
from peekaboo import logger
from peekaboo.ruleset import Result, RuleResult
from peekaboo.ruleset.rules import *
from peekaboo.exceptions import CuckooReportPendingException


'''
# this module contains methods and data structures which allow to
# create a ruleset to decide good or bad for any given file
#
# works together with peekaboo
# and uses cuckoo
'''


def evaluate(sample):
    """
    function that is run by a worker for every Sample object.
    """
    process_rules(sample)
    logger.debug("Rules evaluated")
    report(sample)


def rule(sample, rule_function, args={}):
    """
    rule wrapper for in/out logging and reporting
    """
    function_name = rule_function.func_name
    logger.debug("Processing rule '%s' for %s" % (function_name, sample))

    try:
        if args:
            res = rule_function(sample, args)
        else:
            res = rule_function(sample)

        sample.add_rule_result(res)
    except CuckooReportPendingException as e:
        # in case this our Sample is requesting the Cuckoo report
        raise
    # catch all exceptions in rule
    except Exception as e:
        logger.warning("Unexpected error in '%s' for %s" % (function_name,
                                                            sample))
        logger.exception(e)
        # create "fake" RuleResult
        res = RuleResult("rule_wrapper", result=Result.unknown,
                         reason="Regel mit Fehler abgebrochen",
                         further_analysis=True)
        sample.add_rule_result(res)

    logger.debug("Rule '%s' processed for %s" % (function_name, sample))
    return res


def process_rules(sample):
    s = sample
#                      ____   _   _  _      _____  ____
#                     |  _ \ | | | || |    | ____|/ ___|
#                     | |_) || | | || |    |  _|  \___ \
#                     |  _ < | |_| || |___ | |___  ___) |
#                     |_| \_\ \___/ |_____||_____||____/

# TODO (cuckooWrapper needs to check if there is other samples in pjobs with
# the same hash)
    #p = rule(s, already_in_progress)
    #if not p.further_analysis:
    #    return

    p = rule(s, known)
    if not p.further_analysis:
        return

    p = rule(s, file_larger_than, {"byte": 5})
    if not p.further_analysis:
        return

    p = rule(s, file_type_on_whitelist)
    if not p.further_analysis:
        return

    p = rule(s, file_type_on_greylist)
    if not p.further_analysis:
        return

    p = rule(s, office_macro)
    if not p.further_analysis:
        return

    p = rule(s, requests_evil_domain)
    if not p.further_analysis:
        return

    p = rule(s, cuckoo_evil_sig)
    if not p.further_analysis:
        return

    p = rule(s, cuckoo_analysis_failed)
    if not p.further_analysis:
        return

    p = rule(s, final_rule)
    if not p.further_analysis:
        return

    # active rules, non reporting
#    report(sample)
#    queue_identical_samples(sample) # depends on already_in_progress

#                   __ ____   _   _  _      _____  ____
#                  / /|  _ \ | | | || |    | ____|/ ___|
#                 / / | |_) || | | || |    |  _|  \___ \
#                / /  |  _ < | |_| || |___ | |___  ___) |
#               /_/   |_| \_\ \___/ |_____||_____||____/
    return None


def report(s):
    # TODO: might be better to do this for each rule individually
    s.report()
    if s.get_result() == Result.bad:
        dump_processing_info(s)
    s.save_result()


def dump_processing_info(sample):
    """
    Saves the Cuckoo report as HTML + JSON and the meta info file (if available)
    to a directory named after the job hash.
    """
    job_hash = sample.get_job_hash()
    dump_dir = os.path.join(os.environ['HOME'], 'malware_reports', job_hash)
    os.makedirs(dump_dir, 0770)
    sample_hash = sample.sha256sum

    if not sample.has_attr('cuckoo_json_report_file') or \
       not sample.has_attr('meta_info_file'):
        # Nothing to do, since at least one of the files we need is not there.
        # This is always the case if the result comes from the DB, because
        # a sample has been analysed before.
        return

    logger.debug('Dumping processing info to %s for sample %s' % (dump_dir, sample))

    # Cuckoo report
    try:
        # HTML
        copyfile(sample.get_attr('cuckoo_json_report_file').replace('json', 'html'),
                 os.path.join(dump_dir, sample_hash + '.html'))
        # JSON
        copyfile(sample.get_attr('cuckoo_json_report_file'),
                 os.path.join(dump_dir, sample_hash + '.json'))
    except Exception as e:
        logger.exception(e)
    try:
        # meta info file
        copyfile(sample.get_attr('meta_info_file'),
                 os.path.join(dump_dir, sample_hash + '.info'))
    except Exception as e:
        logger.exception(e)