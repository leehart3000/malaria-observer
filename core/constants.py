"""
Shared constant choices used across apps.
"""

# Known licences for imported datasets. Not exhaustive -- "Other"
# is available for anything not yet listed, so this never blocks adding
# a new dataset while its licence is confirmed. Add entries here as new
# licences are actually encountered, rather than typing them freehand
# per dataset (which is how licence-string drift happens).
LICENSE_CHOICES = [
    ("CC BY 4.0", "CC BY 4.0"),
    ("CC BY-SA 4.0", "CC BY-SA 4.0"),
    ("CC0 1.0", "CC0 1.0 (Public Domain)"),
    ("Other", "Other (see attribution or narrative for details)"),
]
