import collections
import datetime
import tables

p = "/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5"
h = tables.open_file(p, "r")
c = collections.Counter()
for node in h.root.flows:
    for value in node.read(field="TIME_FIRST"):
        month = datetime.datetime.fromtimestamp(
            float(value), datetime.timezone.utc
        ).strftime("%Y-%m")
        c[month] += 1
h.close()
print(dict(sorted(c.items())))
