#!/usr/bin/env python3

import os
import gzip
import json
import itertools

systems_filename = 'systems.json.gz'
named_systems_filename = 'NamedSystems.json.gz'
#sector_lookup_file = 'PGSectorNames.json'
#system_lookup_json = json.load(open(sector_lookup_file, 'r'), strict=False)
#procedural_sectors = { x['PGN'].strip('\t') for x in system_lookup_json['ProceduralGeneratedSectorNames'] }

result = {}

def is_procedural_name(system_name):
    prefix, space, suffix = system_name.rpartition(' ')

    if not space:
        # Single word name, will not be procedural
        return False

    if suffix[0] < 'a' or suffix[0] > 'h':
        # Invalid boxel layer, will not be procedural
        return False

    # TODO: Additional checks on the suffix, but remember there are two forms
    # this can take

    sector_name, space, boxel = prefix.rpartition(' ')

    if not space:
        # Two word name, will not be procedural
        return False

    if len(boxel) != 4 \
    or boxel[0] < 'A' or boxel[0] > 'Z' \
    or boxel[1] < 'A' or boxel[1] > 'Z' \
    or boxel[2] != '-' \
    or boxel[3] < 'A' or boxel[3] > 'Z':
        return False

    # TODO?: Optionally check against known procedural sector names, however
    # non-procedural sectors (e.g. Col 69) that are based on XYZ center point +
    # radius rather than Boxel are not in this set, so would end up listing
    # every system within them as though it has a custom name. On the upside
    # this would allow edgalmap to resolve their System ID without having to
    # know about the list of custom sectors, but would also massively increase
    # the size of the NamedSystems file... I think I'd rather try to hunt down
    # the list of custom sector names (omicron bot on the Indenedent Raxxla
    # Hunters discord definitely had the list before it got shut down) first,
    # and for now hope the above tests are sufficient to catch all custom
    # system names.
    #return sector_name in procedural_sectors
    return True

def process_line(line):
    global result
    j = json.loads(line.rstrip(b',\n'))
    name = j['name']
    if is_procedural_name(name):
        return
    id64 = j['id64']
    #print('%i: %s' % (id64, name))
    if name in result:
        # XXX: Need to understand duplicate names better, e.g. there are four
        # systems named "NGC 2168 SB 987", while other cases are distinguished
        # by capitalisation in the Spansh data (e.g. "R Centauri" vs "r
        # Centauri") but not in edsm.net, and the game is case insensitive
        print('NOTICE: Duplicate system name "%s"' % name)
        if isinstance(result[name], list):
            result[name].append(id64)
        else:
            result[name] = [result[name], id64]
    else:
        result[name] = id64

def save_results():
    with gzip.open(named_systems_filename, 'wt') as output_file:
        json.dump(result, output_file, sort_keys=True, indent=1)
    print("Wrote", named_systems_filename)

def main():
    if not os.path.isfile(systems_filename):
        print('Please save https://downloads.spansh.co.uk/systems.json.gz to this directory')
        return

    s = os.stat(systems_filename)
    filesize = s.st_size

    try:
        with gzip.open(systems_filename) as f:
            # Reading such a large json file all at once is not a great idea,
            # parse + filter one line at a time instead
            assert(f.readline() == b'[\n')
            for i in itertools.count():
                if i and not i & 0xfffff:
                    print('%.2f%% %i' % (f.fileobj.tell() / filesize * 100.0, len(result)))
                    if not i & 0xffffff:
                        save_results()
                line = f.readline()
                if line == b']\n': # EOF
                    break
                process_line(line)
    except KeyboardInterrupt:
        r = ''
        while not r or r.lower() not in 'yn':
            r = input("Interrupted, save partial results? (y/n)")
        if r.lower() != 'y':
            return

    save_results()

if __name__ == '__main__':
    main()
