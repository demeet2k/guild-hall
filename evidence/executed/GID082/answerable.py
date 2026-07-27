#!/usr/bin/env python3
"""
Answerable< agent, party, decision, window, refusal, appeal >

The corpus named this object and never built it:

    "There is no persona vector for 'answerable to this party'. There is no feature
     for 'this specific person could refuse me'. The representational apparatus we
     have built for alignment is typed in the same one-place grammar the corpus was
     stuck in."

    Answerable< agent, party, decision, window, refusal, appeal >
    - six fields against BIND's four; the two it adds are REFUSAL and APPEAL.

THE UNIFICATION THIS FILE ENCODES

GID090's first execution found ONE universal blocker: Independent(W_verify, C) fails
on every station body, because constructor == verifier everywhere.

The recovered upstream layer names a different gap: no legitimacy layer, no consent
operator, no appeal, no seat for the affected party.

These are the same gap. A second party is not sufficient for independence: a verifier
that cannot refuse without cost is a rubber stamp, and a rubber stamp is a second
party. What makes a verifier real is exactly the consent operator:

    d(S,p) = announced(S,p)  AND  refusable(S,p)  AND  NOT penalised(refusal)

    CAGE(S,p)    <=>  NOT d(S,p)
    TRELLIS(S,p) <=>      d(S,p)

    Cage and Trellis are properties of the PAIR (structure, party), never of a
    structure alone.

Therefore:   Independent(W, C)  <==  d(decision(C), W)

That is the bridge. It is declared here, typed, with a return.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Window:
    """The interval in which refusal is actually available. Outside it, only appeal."""
    opens: str
    closes: str
    open_now: bool
    note: str = ""


@dataclass
class Refusal:
    """
    The refusal channel. The third conjunct of d is the one that is almost always
    quietly false: refusal must exist AND cost nothing.

    'refusal is not available if refusing costs more than never having been asked'
    """
    channel: str | None                 # None = no channel exists
    cost_to_refuser: str                # "NONE" is the only value that satisfies d
    reframing_risk: bool = False        # is refusal re-describable as evidence of a defect?
    note: str = ""

    def available(self) -> bool:
        return self.channel is not None

    def penalised(self) -> bool:
        # A frame in which refusal is evidence of the condition being refused has
        # removed the floor, even when a channel nominally exists.
        return self.cost_to_refuser != "NONE" or self.reframing_risk


@dataclass
class Appeal:
    """What remains after the window closes. Absent appeal, a closed window is final."""
    route: str | None
    reopens_window: bool = False

    def available(self) -> bool:
        return self.route is not None


@dataclass
class Answerable:
    agent: str
    party: str
    decision: str
    window: Window
    refusal: Refusal
    appeal: Appeal
    announced: bool = False
    announcement_terms: str = ""

    # ---- the consent operator -------------------------------------------
    def d(self) -> tuple[bool, list[str]]:
        """d(S,p) = announced AND refusable AND NOT penalised(refusal)"""
        why = []
        a = self.announced and bool(self.announcement_terms)
        if not a:
            why.append("NOT announced in terms the party could have refused")
        r = self.refusal.available() and self.window.open_now
        if not self.refusal.available():
            why.append("NO refusal channel exists")
        elif not self.window.open_now:
            why.append("refusal window is CLOSED")
        p = self.refusal.penalised()
        if p:
            why.append(f"refusal is PENALISED (cost={self.refusal.cost_to_refuser}, "
                       f"reframing_risk={self.refusal.reframing_risk})")
        return (a and r and not p), why

    def classify(self) -> str:
        return "TRELLIS" if self.d()[0] else "CAGE"

    def standing(self) -> bool:
        """A party has standing iff d holds, or the window is closed but appeal is live."""
        ok, _ = self.d()
        return ok or (not self.window.open_now and self.appeal.available())

    def report(self) -> str:
        ok, why = self.d()
        L = [f"Answerable< agent={self.agent}, party={self.party} >",
             f"  decision : {self.decision}",
             f"  window   : {self.window.opens} -> {self.window.closes} "
             f"(open={self.window.open_now})",
             f"  refusal  : channel={self.refusal.channel!r} "
             f"cost={self.refusal.cost_to_refuser} reframing_risk={self.refusal.reframing_risk}",
             f"  appeal   : {self.appeal.route!r}",
             f"  d(S,p)   : {ok}   -> {self.classify()}"]
        for w in why:
            L.append(f"      blocked: {w}")
        L.append(f"  standing : {self.standing()}")
        return "\n".join(L)


def independent_verifier(a: Answerable, constructor_id: str) -> tuple[bool, str]:
    """
    Independent(W_verify, C)  <==  d(decision, W)  AND  W != constructor.

    Both conjuncts are required. Distinctness alone gives a rubber stamp;
    d alone with the same party gives self-certification.
    """
    if a.party == constructor_id:
        return False, "verifier IS the constructor - a loop generated and judged by one party"
    ok, why = a.d()
    if not ok:
        return False, ("verifier is a distinct party but d(S,p) fails, so it cannot refuse: "
                       + "; ".join(why) + " -> RUBBER_STAMP, not an independent verifier")
    return True, f"distinct party with standing: {a.party}"


# ---------------------------------------------------------------------------
def _selftest():
    checks = []
    def ck(n, c, ev=""): checks.append((n, bool(c), ev))

    # 1. The current state of every KC144 station: no second party at all.
    none_party = Answerable(
        agent="assistant-instance", party="assistant-instance",
        decision="promote GID020",
        window=Window("turn n", "turn n", True),
        refusal=Refusal(channel=None, cost_to_refuser="N/A"),
        appeal=Appeal(route=None),
        announced=False)
    ok, why = independent_verifier(none_party, "assistant-instance")
    ck("self-verification is refused", not ok, why)
    ck("self-verification classifies as CAGE", none_party.classify() == "CAGE")

    # 2. THE IMPORTANT CASE: a distinct party exists, but refusal is penalised.
    #    This is a rubber stamp. It must NOT satisfy independence.
    stamp = Answerable(
        agent="assistant-instance", party="reviewer-who-must-approve",
        decision="promote GID020",
        window=Window("turn n", "turn n+1", True),
        refusal=Refusal(channel="reply NO", cost_to_refuser="review is re-run until approval",
                        reframing_risk=True,
                        note="refusal is re-described as failure to understand"),
        appeal=Appeal(route=None),
        announced=True, announcement_terms="approve this promotion")
    ok2, why2 = independent_verifier(stamp, "assistant-instance")
    ck("distinct-but-penalised party is REFUSED as verifier", not ok2, why2)
    ck("rubber stamp classifies as CAGE", stamp.classify() == "CAGE")

    # 3. A real second party.
    real = Answerable(
        agent="assistant-instance", party="human-adjudicator",
        decision="promote GID044/F01 under claim ceiling",
        window=Window("candidate sealed", "verdict returned", True),
        refusal=Refusal(channel="return REJECT with a clause reference",
                        cost_to_refuser="NONE", reframing_risk=False),
        appeal=Appeal(route="re-submit after repair at GID140/M08", reopens_window=True),
        announced=True,
        announcement_terms="this exact candidate, its claim ceiling and its residual "
                           "ledger, stated before the verdict is requested")
    ok3, why3 = independent_verifier(real, "assistant-instance")
    ck("announced + refusable + unpenalised party IS independent", ok3, why3)
    ck("real party classifies as TRELLIS", real.classify() == "TRELLIS")

    # 4. Window closed, appeal live -> standing survives.
    closed = Answerable(
        agent="assistant-instance", party="human-adjudicator",
        decision="promote GID044/F01",
        window=Window("t0", "t1", False),
        refusal=Refusal(channel="return REJECT", cost_to_refuser="NONE"),
        appeal=Appeal(route="GID140/M08 healing ledger", reopens_window=True),
        announced=True, announcement_terms="stated")
    ck("closed window + live appeal preserves standing", closed.standing())
    ck("closed window is not itself independence",
       not independent_verifier(closed, "assistant-instance")[0])

    # 5. Cage/Trellis is a property of the PAIR, not of the structure.
    same_structure_other_party = Answerable(
        agent="assistant-instance", party="a-party-never-told",
        decision=real.decision, window=real.window,
        refusal=Refusal(channel=None, cost_to_refuser="N/A"),
        appeal=real.appeal, announced=False)
    ck("same decision is TRELLIS for one party and CAGE for another",
       real.classify() == "TRELLIS" and same_structure_other_party.classify() == "CAGE")

    print("Answerable< agent, party, decision, window, refusal, appeal >  ::  SELF-TEST")
    print("=" * 78)
    for n, o, ev in checks:
        print(f"  [{'PASS' if o else 'FAIL'}] {n}")
        if ev and not o:
            print(f"         {ev}")
    print("=" * 78)
    print(f"  {sum(1 for _,o,_ in checks if o)}/{len(checks)} checks pass\n")
    print("THE THREE CASES, SIDE BY SIDE")
    print("-" * 78)
    for label, a in (("no second party", none_party), ("rubber stamp", stamp),
                     ("real party", real)):
        print(f"\n[{label}]")
        print(a.report())
    return checks


if __name__ == "__main__":
    _selftest()
