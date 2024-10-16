Calculates Elite Dangerous galaxy map addresses that target a specific body within a system.

** As of 3308-09-15 this is of limited usefulness as the galaxy map no longer accepts extended addresses **

Based on the technique described by CMDR Pyroboros:
https://forums.frontier.co.uk/threads/warning-galaxy-map-operating-beyond-safety-limits.598751/

Examples, looking up Sol by the SystemAddress from the player journal:

    ./edgalmap.py 10477373803
    Copied to clipboard: "Wregoe AC-D d12-0"

Looking up Halley's Comet with Sol's custom name (NEW):

    $ ./edgalmap.py Sol -b 21
    Wregoe AC-D d12-0, Body 21
    System Address: 10477373803
    Body Address: 756604747875617131
    Copied to clipboard: "Wregoe AC-D d12-22020096"

Looking up address of the HyperbolicOrbiter of the Thargoid Anomaly at confirmed waypoint 1:

    ./edgalmap.py Oochorrs UF-J c11-0 --body-id 17
    Copied to clipboard: "Oochorrs UF-J c11-2228224"

Looking up address of the HyperbolicOrbiter at predicted waypoint 4, system "HD 38291" body 17 by SystemAddress:

    ./edgalmap.py 1327473756 -b 17
    Copied to clipboard: "Oochorrs GR-V e2-142606336"

Looking up address of the HyperbolicOrbiter at predicted waypoint 12:

    ./edgalmap.py Col 69 Sector LM-U c3-1 -b 28
    Copied to clipboard: "Col 69 Sector LM-U c3-3670017"

Iterate over possibly hidden bodies in the current system (FSS scan everything first, note that this won't search through any gaps in the BodyIDs):

    ./find_bodies.sh
    Current system: Col 69 Sector WL-Q b20-0
    System Address: 677127660481
    Highest bodyID: 8
    
    ./edgalmap.py Col 69 Sector WL-Q b20-0 -b 9
    Copied to clipboard: "Col 69 Sector WL-Q b20-147456"
    
    Press enter to continue to next body, Ctrl+C to abort...
    
    ./edgalmap.py Col 69 Sector WL-Q b20-0 -b 10
    Copied to clipboard: "Col 69 Sector WL-Q b20-163840"
    
    Press enter to continue to next body, Ctrl+C to abort...

Same as above, but use the system address instead of system name (required for named systems):

    ./find_bodies.sh -a
    Current system: Col 69 Sector WL-Q b20-0
    System Address: 677127660481
    Highest bodyID: 8
    
    ./edgalmap.py 677127660481 -b 9
    Copied to clipboard: "Oochorrs QD-P b52-147456"
    
    Press enter to continue to next body, Ctrl+C to abort...
