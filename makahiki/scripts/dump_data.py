#!/usr/bin/python

"""Invocation:  scripts/dump_data.py

Creates a set of json files in the dumped_data directory containing the current state.
This state can be loaded into a new instance using load_data.
"""

import commands
import os

state_pairs = [("teams.group teams.team", "base_teams"),
               ("activities", "base_activities"),
               ("quests", "base_quests"),
               ("help_topics", "base_help"),
               ("auth.user makahiki_profiles makahiki_avatar", "test_users"),
               ("teams.post", "test_posts"),
               ("energy_goals", "test_energy_goals"),
               ("prizes.prize prizes.raffledeadline prizes.raffleprize", "test_prizes")]
"""Tuples of (<state info to extract>, <json file name in which to write the data>)."""


def main():
    """main"""

    # Ensure dump_dir/ exists, creating it if not found.
    dump_dir = os.path.dirname("dumped_data/")
    if not os.path.exists(dump_dir):
        os.makedirs(dump_dir)

    #Loop through all state_types, dump the data, then write it out.
    for state_pair in state_pairs:
        command = "python manage.py dumpdata --indent=2 " + state_pair[0]
        (status, output) = commands.getstatusoutput(command)
        if status:
            print "Error obtaining " + state_pair[0] + " skipping. (" + output + ")"
        else:
            output_file = os.path.join(dump_dir, state_pair[1] + ".json")
            print "Writing " + output_file
            with open(output_file, "w") as out:
                out.write(output)


if __name__ == '__main__':
    main()
