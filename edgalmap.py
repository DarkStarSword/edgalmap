#!/usr/bin/env python

import json
import winclipboard
import argparse
import sys, os

# https://forums.frontier.co.uk/threads/warning-galaxy-map-operating-beyond-safety-limits.598751/
layers_map = {
        0: 11,
        'a': 11,
        1: 14,
        'b': 14,
        2: 17,
        'c': 17,
        3: 20,
        'd': 20,
        4: 23,
        'e': 23,
        5: 26,
        'f': 26,
        6: 29,
        'g': 29,
        7: 32,
        'h': 32,
}
def b(cube_layer, body_id):
    return body_id << layers_map[cube_layer]

sector_lookup_file = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'PGSectorNames.json')
system_lookup_json = json.load(open(sector_lookup_file, 'r'), strict=False)
system_loopup_map = { x['Key']: x['PGN'] for x in system_lookup_json['ProceduralGeneratedSectorNames'] }
def system_lookup_key(sector_x, sector_y, sector_z):
    # "Key" seems rather unnecessary - could just take SectorX/Y/Z as a tuple and use that as the key...
    # Or better yet, the file could have been formatted to use a json map >_<
    # But anyway...
    return sector_x | sector_y<<7 | sector_z<<14
def lookup_sector_name(sector_key):
    return system_loopup_map[sector_key]

def s_by_name(system_name, body_id):
    suffix = system_name.rpartition(' ')[2]
    if suffix == system_name or suffix[0].lower() not in 'abcdefgh':
        print('Malformed system name:', suffix)
        return
    cube_layer = ord(suffix[0].lower()) - ord('a')
    system_id = suffix[1:].rpartition('-')[2]
    if not system_id.isnumeric():
        print('Malformed system ID:', suffix)
        return
    #print(cube_layer, system_id)

    system_name = system_name[:-len(system_id)] + str((int(system_id) + b(cube_layer, body_id)))
    winclipboard.copy_text_simple(system_name.encode('ascii'))
    print('Copied to clipboard: "%s"' % system_name)

def s(system_address, body_id=0):
    if isinstance(system_address, str):
        return s_by_name(system_address, body_id)

    def get_bits(n):
        return system_address >> n, system_address & 2**n-1
    system_address, cube_layer = get_bits(3)
    boxel_bits = 7 - cube_layer
    #print('layer', cube_layer)
    #print('boxel_bits', boxel_bits)
    system_address, boxel_z    = get_bits(boxel_bits)
    system_address, sector_z   = get_bits(7)
    system_address, boxel_y    = get_bits(boxel_bits)
    system_address, sector_y   = get_bits(6)
    system_address, boxel_x    = get_bits(boxel_bits)
    system_address, sector_x   = get_bits(7)
    system_id_bits = 11 + cube_layer*3
    #print('system_id_bits', system_id_bits)
    system_address, system_id  = get_bits(system_id_bits)
    system_address, body_id_a  = get_bits(9)
    #print('sector', sector_x, sector_y, sector_z)
    #print('boxel', boxel_x, boxel_y, boxel_z)
    #print('system_id', system_id)
    #print('body_id', body_id_a)
    if body_id and body_id_a:
        print("Address already included BodyID %i, don't use -b %i" % (body_id_a, body_id))
        return 1
    elif body_id_a:
        body_id = body_id_a
    try:
        sector_key = system_lookup_key(sector_x, sector_y, sector_z)
        sector_name = lookup_sector_name(sector_key).strip('\t')
    except KeyError as e:
        print('Sector missing from PGSectorNames.json, please add an entry such as this with PGN filled out:')
        print('{"Key": %i ,"PGN":"","Position":{"SectorX": %d, "SectorY": %d, "SectorZ": %d}},' % ( \
            sector_key, sector_x, sector_y, sector_z
        ))
        return
    #print('sector', sector_name)
    boxel_key = boxel_x | boxel_y<<7 | boxel_z<<14
    def to_letter(n):
        return chr(ord('A') + n)
    boxel_letter_a  = to_letter(boxel_key  % 26)
    boxel_letter_b  = to_letter(boxel_key // 26  % 26)
    boxel_letter_c  = to_letter(boxel_key // 26 // 26  % 26)
    boxel_remainder = boxel_key // 26 // 26 // 26
    system_name = '%s %s%s-%s %s' % \
            (sector_name,
            boxel_letter_a,
            boxel_letter_b,
            boxel_letter_c,
            to_letter(cube_layer).lower())
    if (boxel_remainder):
        system_name += '%d-' % boxel_remainder
    if body_id_a:
        # Body ID was included in the address cryptically, and we are about to
        # send it to the clipboard cryptically... show the readable ID as well
        print("%s%s, Body %i" % (system_name, system_id, body_id))
    system_name += '%s' % (system_id + b(cube_layer, body_id))
    winclipboard.copy_text_simple(system_name.encode('ascii'))
    print('Copied to clipboard: "%s"' % system_name)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Warning: Galaxy Map Operating Beyond Safety Limits!")
    parser.add_argument('-b', '--body-id', type=int, default=0, help='BodyID to target')
    parser.add_argument('system', nargs='+', help='System name (generic names only) or numeric SystemAddress from journal (required for named systems)')
    args = parser.parse_args()
    system = ' '.join(args.system)
    if system.isnumeric():
        system = int(system)
    s(system, args.body_id)
