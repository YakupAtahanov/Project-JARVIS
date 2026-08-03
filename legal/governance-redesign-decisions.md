# Governance & Licensing Redesign — Decisions Log

> **Status:** Working record of design decisions, captured live as they are settled.
> Not yet drafted into the operative documents (SCCL-v1.md, organization-charter.md,
> cla.md, c-points.md). This log is the source of truth for *what we decided*; the
> redrafts implement it. Still a DRAFT and still pending legal counsel review.

---

## Mission framing (the three pillars every decision serves)

1. **A legal standout against acquisition and abuse** — the code and community cannot be
   bought, captured, or turned to bad ends.
2. **Compensated meritocracy** — the people doing load-bearing work get paid in proportion
   to merit, so "unpaid solo maintainer" never becomes the attack surface (the XZ lesson).
3. **Durability past the founder** — if it needs the founder in the room to stay on the
   rails, it has failed. It must launch and survive without them.

Scope note: the framework is intended to be **reusable across every project under the
Foundation** (Project JARVIS, ForgeHub, and others), not JARVIS-specific. Making the
documents project-agnostic/parameterized is a tracked open item.

---

## A. Licensing / pricing decisions

**A1. The SCCL is a revenue product, not a pure deterrent.** Companies are meant to sign
and pay. Consequently the fee must be signable by a general counsel.

**A2. The community sets the bill; the Board administers it.** The community ratifies the
fee *formula and the published criteria* (policy); the Board *applies* that published
formula to each licensee (administration). A licensee can always see how its number was
derived from public criteria + its own behavior. (Implements existing SCCL 4.2.1 / Charter
B.6.4.)

**A3. Behavior reduces the fee — through *published, objective* criteria only.** The main
lever is the **inclusion index** (Appendix A.4: data portability, API openness,
interoperability, switching cost, platform dependency) — published methodology with worked
examples. Good-faith, open, interoperable conduct → low index → near-zero fee, provable to
the licensee's own board. Good faith is assessed on the company's conduct broadly, not only
toward Foundation projects.

**A4. The Relationship Index comes OUT of the pricing path.** It survives as an internal
relationship tool (whether to *issue*, whether to *renew*, cure-period generosity) but is
never a secret multiplier on the bill. Rationale: a secret per-licensee price score is
unsignable and creates antitrust/discrimination exposure.

**A5. Revenue Basis tier is signed into the contract and constant for the term.** No
mid-term re-selection.

**A6. Term is one year, renewed thereafter.** Renewal is the re-assessment checkpoint: the
past year's conduct feeds next year's inclusion index and tier. Longer fixed terms (2–3 yr)
may be offered with the tier fixed for the whole term; annual is the default.

**A7. The AGPLv3 exit is the pressure-relief valve.** At every renewal a licensee that
dislikes the new terms can decline and fall back to AGPLv3 compliance (or cease use). This
is what keeps the scheme non-coercive and enforceable — nobody is trapped.

---

## B. Governance decisions

**B-Q1. Durability model = two-tier ("freeze values, repair mechanics").** *(Option A.)*
A small **immutable values core** is frozen forever; **everything else** (voting formulas,
stage triggers, C-points measurement, fee formula) is amendable ONLY through a
capture-resistant dual-key path: **Board supermajority AND community supermajority**, with
90-day public notice, and a one-way ratchet — **no amendment may ever net-reduce community
power or the compensation floor.** This is what makes the framework incorruptible in what
matters yet repairable in what breaks — the precondition for fixing the known voting bugs
at all.

*Immutable values core (initial list — to be finalized):*
- **Meritocratic source of authority** (see B-Q1a wording below)
- 50% contributor compensation floor (current B.5.1)
- Dissolution asset-lock — assets never to a Board member or licensee (current B.7.3)
- No Board self-dealing
- One-way ratchet: community power and the compensation floor may only grow, never shrink

**B-Q1a. Meritocratic source of authority — immutable wording (APPROVED):**

> Governance authority derives solely from merit — the demonstrated contribution of labor
> to the commons — and never from capital, ownership, purchase, or any commercial
> relationship. No governance seat, vote, or influence may be exchanged for money or
> commercial consideration. The only permitted non-merit seats are those expressly
> enumerated and time-bounded in this Charter [founder seats, which sunset; one independent
> expert seat barred from any licensee tie]; no amendment may create additional exceptions,
> and no amendment may redefine "merit" to include capital, ownership, or commercial
> relationship.

Design notes:
- Bundles the **positive** rule (merit is the only *earned* path to power) and the
  **negative** rule (money is never a path) — each closes a gap the other leaves open.
- **Trap 1 resolved:** founder and independent seats are the *only* enumerated non-merit
  exceptions, and the list is itself locked so a captured process can't invent new
  "exception" seats.
- **Trap 2 resolved:** merit's *basis* (labor to the commons) is frozen; merit's
  *measurement* (the C-points formula) stays amendable, so the tier can refine how labor is
  measured but can never redefine merit to mean capital.

**B-Q1b. Founder seats: special power sunsets; the seat converts to elected.** Superseded by
and folded into **B-Q2** below (the seat converts to a normal elected seat rather than being
abolished, keeping board headcount constant).

---

**B-Q2. Founder → community handoff.**

**The seat and the special power are decoupled — they end at different times.**

- **Two founders total** for the entire Foundation.
- **During bootstrap:** each founder holds a **founder seat** — appointed, carrying the
  deliberate out-of-bounds "voice" that lets the founders steer while the community is thin.
- **The special power wanes stage by stage** (the staged-governance model, B.9): founders
  hold progressively less power until, at the final stage, the Foundation belongs to the
  community.
- **The seat never vanishes — it *converts* to a normal Pool-Elected seat**, one-by-one as
  each founder steps back, so board headcount stays constant. (Supersedes the earlier
  "cease to exist entirely" note.)
- **After conversion, a founder may keep serving as an *ordinary* member** — ordinary
  member leverage only (bring questions, vote); **no veto, no weighted vote, no tiebreak** —
  and with **no special tenure protection**: they persist only as long as the community keeps
  them, via the same confidence/election mechanism as anyone.

**No codified for-life founder seat.** A written for-life seat would violate the immutable
meritocracy rule (B-Q1a: authority from merit, not founder status). The founders' long-term
presence is achieved only through the ordinary elected mechanism — earned continuously, not
granted. This is deliberate: the founders binding themselves to the identical rules is the
credibility engine for the whole framework ("no one is above the rules, including the people
who wrote them").

**Special-power sunset trigger (durability backstop).** A founder's *special power* ends at
the **earliest of**: (a) voluntary step-back; (b) death/incapacity (→ Designated Successor
bridge per B.3.6, then election); or **(c) Stage 4 activation OR a hard maximum of ~10 years,
whichever comes first.** Trigger (c) guarantees the special power ends *even if a founder
never retires and never dies* — closing the founder-dependence gap. When (c) fires, the seat
converts to normal-elected and a still-serving founder continues as an ordinary member.

**Board size.** Steady-state target **15** (odd → no tie votes; 2 founders ≈ 13% → not
dominant). The board **scales toward 15 as the community grows** — small during bootstrap
(2 founders + 1 independent + a few elected), reaching full size by maturity. Mature
composition: **2 founder-origin (converted to elected) + 1 Independent Seat + 12
Pool-Elected.** (Changes current B.3.1's "5–9 members.")

*Open micro-choices to confirm:* value of N for the hard-year cap (proposed ~10);
scaling schedule for board growth (how seats are added per stage).

---

**B-Q3. Board removal = auto-elimination via the health bar.** Replaces the broken B.3.3
Continuous Confidence Vote. **(REVISED — supersedes the earlier "B+C hybrid" where a health-bar
*signal* triggered a discrete recall *vote*. The health bar now eliminates DIRECTLY; the
separate vote, its turnout quorum, and the old anti-harassment "Cooldown B" are all gone.
Adopted at the founder's request for simplicity + always-on accountability; made safe by the
whole-Pool anchor below.)**

**Guiding principle (founder's framing):** a board member can never predict when their time
is up; the only way to extend it is to keep serving the community's needs, rules, and conduct.
Accountability through uncertainty. Silence protects a member doing well (silence = keep).

**Mechanism — direct auto-elimination:**
- Each Pool member may hold a **"replace"** position on any board member (default = no
  position = keep); positions are changeable anytime; the live tally is public.
- A board member is **auto-eliminated** when "replace" positions reach **≥ threshold% of the
  current Pool snapshot**, held continuously for a **sustain window of N days**.
- **The non-negotiable anchor — absolute fraction of the WHOLE Pool, not of turnout.** Passive
  members count as keep, so removal requires a genuine broad slice of the entire ~1,000-member
  governance body; a small low-turnout bloc cannot do it. This is exactly what makes direct
  auto-elimination safe rather than the original capture bug. It also dissolves the old
  auto-seed ambiguity (count replace against the whole-Pool denominator; not-voting = keep —
  no ratios, no quorum-of-turnout).
- **Sustain window (N days)** defeats a momentary coordinated spike.
- **Two-bar decrement (repeat-offender escalation — founder's design):** the elimination
  threshold starts at a **high bar** for a first-term member and **steps down** toward a
  **low-bar floor** with each removal-and-return — the community's repeated "we want this
  person out" makes them progressively easier to remove.
  - Tied to **involuntary removals only** (not clean resignation or founder-seat conversion).
  - **Decays over a rolling window** (no permanent marks — consistent with the Integrity
    Multiplier philosophy).
  - **Floor stays strictly ABOVE the 20% employer cap**, so no single employer can ever
    eliminate a member alone — even a many-times-removed one (closes the "employer drives a
    rival's champion down to self-removability" attack).
- **Replacement is automatic, from an opt-in candidate pool (refined in B-Q6).** Candidacy is
  opt-in — the system maintains a standing pool of volunteers. On a vacancy the seat auto-fills
  with the **highest-merit (C-points) opt-in candidate**, respecting the employer-diversity cap
  — NOT chosen by the recall voters (which would let a removing faction also pick the crony).
  Fully automatic; the meritocracy metric does the choosing. Edge cases (empty pool, ties, cap
  conflicts) to be enumerated.
  - **Opting out carries ZERO penalty.** A contributor who declines board candidacy keeps all
    C-points, pay, and Pool membership — they simply aren't in the candidate pool (and get
    their earned time off). Leadership is an earned rotation one *accepts*, never a draft;
    availability to serve is a personal choice, never a merit judgment (mirrors B-Q3a).
- **Cooldowns after the pivot:** *Cooldown A* (post-removal re-entry, B-Q3b) is **kept**;
  *Cooldown B* (the old anti-harassment recall-reattempt cooldown) is **removed** — there is
  no failing vote to re-launch. Repeat-offender escalation now lives in the health-bar
  **decrement** above, not in cooldown length.
- **Honest trade-off (logged):** direct auto-elimination is *less responsive* than a bounded
  vote for a *first-term* bad member (it needs sustained active "replace" positions, vs.
  mobilizing a voting window). The decrement mitigates this for repeat offenders; accepted for
  the simplicity + always-on-accountability gain.

**B-Q3b. Post-removal re-eligibility cooldown (distinct clock).** A *removed* member is pulled
from the opt-in candidate pool for a cooldown before they can be re-assigned. **Necessary,
not optional:** removal does not touch C-points, so without a cooldown the removed member —
still the highest-merit opt-in candidate — would auto-fill the very vacancy their removal
created, making removal a revolving door.
- **Governance timeout only** — the cooldown never touches C-points, pay, or Pool membership
  (consistent with B-Q3a and opt-out-no-penalty). A removed member remains a full contributor
  who earns and votes; they simply cannot *govern* during the cooldown.
- **Two edge cases:** (a) **repeat-offender escalation now lives in the health-bar decrement**
  (B-Q3), not in cooldown length — so **Cooldown A can stay flat (~3 months, founder-proposed)**;
  (b) **resigning to dodge an active/imminent removal counts as removal** (else a member resigns
  "cleanly" and re-qualifies immediately).
- **Board-member lifecycle:** opt in → assigned (highest-merit opt-in candidate, fresh health
  bar) → serve (health-bar accountable) → removed/resign/convert → cooldown → return-eligible.
- Cooldown A length (~3 months) is a tuning-pass number.

**Bugs this fixes:** kills the auto-seed "cast votes" ambiguity (silence = keep; replace
measured against the whole-Pool snapshot); raises the minimum capture bloc from **~5% to a
broad absolute fraction of the Pool** (and, with the 20% Employer Concentration Limit and the
above-cap floor, forces cross-employer coordination at every threshold level).

**Shared fixes (apply regardless):** measure all thresholds against the **Pool snapshot**
(top-N by C-points, which already excludes trivial-merge gaming) rather than raw "Active
Contributors," and fix the snapshot date (B-Q6a) so the denominator can't be inflated mid-run.

**Thresholds to derive (tuning pass, founder-flagged):** with a fixed ~1,000-member Pool, the
high bar, the low-bar floor (must be > 20%), the per-removal decrement step, the decay window,
and N (sustain days) can all be derived from that figure — "we would need to think about it."

*Note:* this mechanism governs the founders' converted (ordinary) seats too — capture-
resistant but still responsive, protecting founders and community alike.

---

**B-Q3a. Board compensation stays OFF the C-points rail. (Recommended — pending confirm.)**
Board/administrative service is **not** awarded C-points. Rationale: C-points confer Pool
rank + pay + board eligibility, so C-points-for-office would (1) violate the immutable
meritocracy rule (authority would derive from holding office, not from labor to the commons),
(2) build a self-perpetuation/incumbency ratchet — the exact capture vector the design fights,
(3) constitute board self-dealing, and (4) contradict B-Q3's healthy impermanence (it
incentivizes clinging to the seat). Instead, keep the existing separation (c-points §7.4):
- **Pure board/admin labor → a transparent stipend from the operations slice** (SCCL 4.7(f)),
  which may be made meaningful and is published in the annual report.
- **Genuine commons work by a board member → earns C-points for the *work*, not the office**,
  on equal footing with every contributor (dimensions 5/7/8 already capture triage,
  mentorship, leadership).
- Line: **C-points are earned for building the commons, never for holding a seat.**

**B-Q3a (refinement). The board stipend is variable, via a community-ratified formula —
not a constant.** Recomputed annually from objective inputs:
1. **Foundation capacity** — a small function of revenue/reserves (→ 0 when pre-revenue/lean).
2. **Economic adjustment** — a CPI/cost-of-living index so real value holds.
3. **Self-scaling cap** — never exceeds *median contributor compensation* (existing B.5.5),
   a cap that automatically tracks foundation health.
Guardrails: the **formula is community-ratified, not board-set** (board applies it to the
year's numbers — never votes its own pay → no self-dealing); published in the annual report.

---

**B-Q5. Safe path to Stage 4 — the bootstrap as founder-stewarded incubation.**

**Framing (founder).** Stages 1–3 are not about founders holding power; they are a
founder-stewarded **incubation** whose job is (a) build the machine Stage 4 runs on and
(b) shield the project from acquisition/abuse while it is too fragile to defend itself.
Founder authority is a **caretaker role with a guaranteed expiry**, time-bounded by objective
maturity criteria the founders cannot extend — which dissolves the "autocracy vs. handoff"
tension (trusteeship during construction, not open-ended power).

**Founder backstop (minimal).** Heavy community recall of founders during Stages 1–2 is
impractical (tiny electorate) and set aside. Keep only a **two-key** requirement (both
founders, or founder + independent seat) for genuinely irreversible acts — justified by the
Designated Successor case (a founder seat may be held by a successor whose good character we
do not assume; same logic as B.3.6's licensee-affiliation bar), not distrust of the founders.
The immutable core (B-Q1) + legal/fiduciary duties apply at all stages regardless.

**"Mature enough" = two axes:**
- **Community-ready** — enough *genuine, diverse, durable* contributors.
- **Machine-ready** — the foundation's **"life engine"** (its autonomic organs) is built and
  proven for what the next stage activates. Organs: electoral (+ Q6 plumbing), C-points/merit,
  compensation/payment rails, licensing/registry, transparency/reporting, governance-state.
  **Hard rule: no founder may be a single point of failure in any organ** — every organ must
  be operable by the *institution*, not a specific person. This is the operational meaning of
  "survives after the founder."

**Four robustness properties on every threshold:**
1. **Inflation-proof base** — count non-trivial / C-point-qualified contributors on a fixed
   snapshot (never "anyone with one merged PR").
2. **Sustained** — thresholds hold for N consecutive months (defeats a manufactured surge).
3. **Employer-diversity precondition** — no single employer group exceeds X% of the
   qualifying base. *The anti-acquisition heart:* never advance to more community power, and
   never hand off, while one entity could dominate the resulting community.
4. **Automatic + challengeable + independently verified** — fires when met (founders can't
   stall); any contributor may challenge; verification is independent.

**Per-transition (numbers illustrative, to tune):**
| Transition | Community-ready | Machine-ready |
|---|---|---|
| 1 → 2 | ~15 non-trivial, no employer > ~40%, sustained ~3 mo | Transparency organ live |
| 2 → 3 | ~30–50, no employer > ~⅓, sustained ~6 mo, ≥1 elected seat filled w/ real turnout | Electoral + C-points + compensation rails built & dry-run |
| 3 → 4 | B-Q4 staffing test (full employer-diverse elected board + turnout + sustained health) | Whole machine proven in production |

**No licensee count at any transition** — governance progression decoupled from commercial
sales at every stage (consistent with B-Q4). Closes the "progression hostage to sales"
circular dependency.

**Anti-acquisition payoff (encoded, not personal):** an acquirer who *floods* contributors to
force/pack a handoff fails properties #2 + #3; one who *stalls* to keep Stage 3 fails #4 + the
B-Q4 staffing trigger. The founders' protective role becomes a permanent automatic property
that outlives them.

**Diversity precondition scope: Stage 2 onward (confirmed).** Not gated at Stage 1 (~15
people, no community power to capture yet; the two-key + immutable core cover Stage 1). From
Stage 2, where community influence begins to matter, it is a hard gate.

*Open micro-choices (deferred to end-of-pass tuning):* the N-month sustain windows and
%/headcount thresholds; the explicit machine-ready checklist per organ.

---

**B-Q4. Stage 4 activation = "staff a legitimate board" trigger; irreversible.** Replaces
the broken B.9.4 (neutral-band override + inflatable denominator).

**Intent (founder):** bias the design so the handoff *actually happens* in most cases — the
real threat is a minority bloc *blocking* it (adversarial risk #3), not it occurring. The
meter is **foundation health**, NOT licensee count (decoupled from commercial sales).

**Mechanism — the founding board election IS the trigger:**
- **Precondition:** a genuinely populated Pool sustained for **N months**, measured against
  the inflation-proof snapshot (kills the trivial-merge denominator attack).
- **Trigger:** an election opens for all non-founder seats. **Stage 4 activates iff the
  community elects a full slate** — all 13 non-founder seats filled, satisfying the
  employer-diversity cap (no bloc dominates the new board), with turnout above an absolute
  floor.
- **Staffing is the consent signal** — electing a full, diverse board is a stronger "ready
  and willing" than any yes/no poll, so **the buggy 3-band vote is deleted entirely.**
- **Can't be blocked by a minority** (abstention can't stop a willing majority from meeting
  the turnout floor) → closes adversarial risk #3. **Can't be forced by a clique** (can't
  fake 13 diverse elected candidates + turnout; employer-diversity gate fails a captured
  slate). A "not yet" is natural — stays Stage 3, retry later.

**At activation:** the two founder seats **convert in place** (special power ends per B-Q2
trigger (c)); founders continue as ordinary incumbents subject to B+C recall. The founding
election fills the seats around them. Founder autocracy ends exactly here.

**Irreversible (confirmed).** No return to founder control, ever — a reversible handoff is
not a handoff ("it forces our stay; not a true handoff"). Post-handoff safety comes NOT from
reversal but from the **immutable values core (B-Q1)** binding even a captured Stage-4
community + the employer cap + B+C recall. Ultimate backstop is dissolution (B.7.3), not
reversal. *Irreversible stage + immutable values = permanent self-governance that cannot
self-destruct the guarantees.*

*Open micro-choices:* value of N (sustained-health months); the turnout-floor value on the
founding election; whether a genuine majority may still *delay* a ready activation (light
safety) or staffing-alone governs.

---

**B-Q6. Electoral integrity — the plumbing under every vote/petition/quorum.**

**Key insight:** the meritocracy already provides most Sybil-resistance — governance votes
require earned C-points, and a fake electorate (100 contributors each with real non-trivial
merge history) is prohibitively expensive to manufacture. Q6 closes only the residual gaps.

**B-Q6a. Snapshot rule.** Every threshold (petition %, turnout quorum, election roster) is
measured against the electorate **frozen at a published record date** — the Pool as of the day
the action opens. New/removed contributors during the window do not change the roster or the
target. (Like a shareholder-vote record date.) This is the concrete definition of the
"inflation-proof snapshot" referenced in B-Q3/B-Q4/B-Q5 — it hardens every mechanism at once.

**B-Q6b. Petition electorate = the Pool.** Only Governance Pool members (top ~1,000 by
C-points; = all active contributors while under 1,000) may **create and sign** petitions. The
Pool becomes the single enfranchised body for binding governance actions (petitions, recalls,
ratifications) — the same body that legislates at Stage 4. Replaces the vaguer "Active
Contributors" petition electorate. Primary anti-spam measure (Pool membership is hard to fake).

**B-Q6b-2. Pool recalculation cadence — three distinct clocks.**
- **C-point *scores*: continuous** (always current).
- **Pool *roster*: biweekly** (governance eligibility). Safe to refresh this often because
  C-points are a slow 24-month rolling metric (no spike-in gaming); biweekly keeps governance
  power coupled to *currently active* merit (a departed contributor loses standing in ~2 weeks,
  mildly better for anti-capture). Per-vote stability is handled by the snapshot rule (B-Q6a),
  so a mid-process refresh never disrupts a vote in flight. Boundary flicker at rank ~1,000 is
  an accepted, harmless edge.
- **Compensation *snapshot*: monthly** (aligned with payouts + tax/reporting). No conflict with
  the biweekly governance roster because pay is not Pool-gated.

**B-Q6c. Administration + audit.** An election authority **independent of the Board** runs and
certifies tallies; the independent auditor (B.5.6) reviews electoral records. The Board never
counts votes about itself.

**B-Q6d. Anti-spam.** Petition cooldowns, one active petition per subject, a minimum
distinct-verified-signer count, per-subject rate caps (fixes the missing repeat-petition
rate-limit the adversarial doc flagged).

**B-Q6e. Proportionate, opt-in identity.**
- **Contribute + earn C-points → fully pseudonymous, no identity, no pressure, ever.**
- **Identity is opt-in — triggered only by choosing a power/money action:** cast a binding
  vote, receive compensation, or stand for the Board. A contributor who never does these never
  provides identity.
- **Compensation:** earning is pressure-free/pseudonymous; *claiming the money* requires
  identity (tax/KYC — legally unavoidable). Unclaimed comp is escrowed, returns to the pool
  after a window.
- **Privacy-preserving verification:** verify once → derive a non-reversible "one-human" token
  → **delete the raw ID documents promptly** (better than a 3–5 yr hold); keep only the token
  for Sybil-resistance.
- **Retention exception:** payment-linked identity has a **legally-mandated tax-record
  retention** (several years — counsel to confirm) that overrides fast deletion. So:
  voting-only identity → delete fast; paid identity → legal minimum, then delete.

*Open:* exact cooldown/rate-limit values; the uniqueness-token method (proof-of-personhood
vs. third-party attestation vs. tax-identity reuse); confirm tax-retention figure with counsel.

---

## Open questions (governance walkthrough, in order)

- [x] **Q2 — Founder → community handoff.** *Settled (see B-Q2).* Two micro-choices left open:
      the N-year cap value and the board-growth schedule.
- [x] **Q3 — Board removal/replacement math.** *Settled (see B-Q3): DIRECT auto-elimination via
      the health bar (whole-Pool absolute threshold + sustain window + two-bar decrement),
      revised from the earlier B+C-vote model.* Board comp stays off the C-points rail (B-Q3a).
- [x] **Q4 — Stage-4 activation trigger.** *Settled (see B-Q4): staffing-as-trigger,
      health-metered, irreversible.* Micro-choices (N months, turnout floor, delay-veto) open.
- [x] **Q5 — Safe path to Stage 4.** *Settled (see B-Q5): incubation model, two-axis maturity
      (community-ready + machine-ready "life engine"), four robustness properties, decoupled
      from licensees.* Micro-choices (diversity-gate scope, thresholds, machine checklist) open.
- [x] **Q6 — Electoral integrity.** *Settled (see B-Q6): snapshot rule, Pool-only petitions,
      independent audit, anti-spam, proportionate opt-in identity.* Values open for end tuning.

---

## Session handoff — current status & what's next

**Where we are.** The governance redesign (Q1–Q6) is fully designed and internally consistent,
captured above. The pricing model (A1–A7) is settled. This log is the authoritative spec; the
operative documents (SCCL-v1.md, organization-charter.md, cla.md, c-points.md) have NOT yet
been rewritten to match it.

**Open — numbers (deferred to one end-of-pass tuning round):**
- Founder-seat hard-year cap N (B-Q2, proposed ~10); board-growth schedule per stage.
- Board-removal thresholds (B-Q3): high bar, low-bar floor (> 20%), decrement step, decay
  window, sustain days N — all to be *derived from the fixed ~1,000-member Pool* (founder's
  next thinking task).
- Cooldown A length (~3 months); Cooldown B suggestion is now moot (removed in the B-Q3 pivot).
- Stage-maturity thresholds (B-Q5): sustain windows, %/headcount, per-organ machine checklist.
- Electoral-integrity values (B-Q6): cooldown/rate-limit numbers, uniqueness-token method.

**Open — big items NOT yet touched (these gate whether the governance can legally exist):**
1. **Inbound rights chain** — the Foundation cannot currently relicense community code (DCO +
   AGPLv3 only). Needs a universal FLA/ICLA-style inbound grant + B.2.4 rewrite + retroactive
   consent sweep. (See the pre-counsel review report for detail.)
2. **Entity form** — 501(c)(3) is likely the wrong vehicle for selling licenses + distributing
   most revenue to contributors; evaluate 501(c)(6) / alternatives with counsel; statutory
   membership structure to make Stage-4 community power lawful.
3. **Redraft the operative documents** from this log (the big lift), plus the mechanical
   cleanups from the review (stale root SCCL copy, CLA name error, cross-reference fixes).

**Suggested next step:** tackle the two foundation problems (1 & 2) — beautiful governance on an
un-relicensable codebase or the wrong entity is a house on sand — then redraft. Or run the
number-tuning round first if you'd rather lock the mechanics.

---

*This log is appended as each question is settled. When the governance pass is complete, the
decisions here are drafted into the operative documents in one reviewed change.*
