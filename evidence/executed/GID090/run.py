from ic10 import I10, report
from candidates import ALL
print("="*78)
print("GID090 / IC10-I10 :: FIRST EXECUTION")
print("="*78)
res=[]
for c in ALL:
    r=I10(c); res.append(r)
    print(); print(report(r))
print(); print("="*78); print("SUMMARY"); print("="*78)
for r in res:
    print(f"  {r.verdict:20s} {r.candidate_id}")
print()
from collections import Counter
print("  verdicts:", dict(Counter(r.verdict for r in res)))
print("  promotions issued:", sum(1 for r in res if r.verdict.startswith('PROMOTE')))
