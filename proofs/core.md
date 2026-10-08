# Core semantics and arguments

These are complete prose arguments for the restricted mathematical model below,
not proof-assistant-checked theorems. Executable checks are described separately
in `docs/validation.md`. The symbolic backend is trusted for unsatisfiability.
No result in this file verifies a repository patch without a correct source map.

## 1. Language and observations

A parameter vector n ranges over integers subject to a Boolean combination Phi
of affine comparisons. Every input and output shape is affine in n. A shape s
has coordinates D(s) = {i : 0 <= i_k < s_k for all k}. The empty rank-zero tuple
has one coordinate. A positive-rank shape with a zero dimension has none.

An input cell is a pair (x,b), with x rational and b Boolean, satisfying not b
implies x=0. Stored zeros are allowed. Input tensor identities are distinct and
have no alias relation. A program is an output shape, one logical storage policy,
and a finite ordered list of terms (tensor A, affine address a(n,i), rational
constant c, affine Boolean guard g(n,i)). It returns the exact rational sum of
c*x_A(a(n,i)) over active terms. Input values never select guards.

Storage policies are dense (always true), empty (always false), compact (sum is
nonzero), and union (some active read's input cell is stored). Zero-coefficient
reads still participate in union. Potential-term order is the list of active
(tensor identity,address,normalized coefficient) tuples, independent of input
occupancy. It is not an actual sparse execution or floating-point reduction trace.

Admission requires: Phi is satisfiable; every dimension is nonnegative throughout
Phi; every active read at every output coordinate is in bounds; and every
empty-stored output is universally zero. Unsupported syntax, invalid semantics,
vacuous preconditions and unknown queries are separate statuses, not grades.
Feasible empty output domains are legal. Output-shape disagreement is graded,
not automatically treated as invalid.

S means universal output-shape equality. Each other atom includes S and, at equal
shapes, universal equality of: numerical values V; zero/nonzero locations Z;
occupancy M; or potential-term lists O. Thus O implies V implies Z implies S,
and M implies S. Strength is inclusion of guaranteed atoms. The nine closed
sets are empty, S, SM, SZ, SZM, SZV, SZVM, SZVO, SZVOM.

## 2. Exact scalar encoding

For each read occurrence introduce x_j in Q and b_j Boolean, with not b_j =>
x_j=0. For occurrences on the same tensor, impose equal concrete addresses =>
equal x and equal b. Keep shape and selected output coordinates symbolic integers.
Values are finite guarded sums; occupancy follows its policy. The order test
compares active counts and the tuples at matching active-prefix positions.
The bad formula for a nonshape atom is Phi AND well-formedness AND congruence
AND (shape mismatch OR (coordinate in both output domains AND observation mismatch)).
The shape query uses shape mismatch alone after the common constraints.

**Theorem A.** For every admitted pair, an atom's bad formula is satisfiable iff
there is a legal concrete failure.

**Proof.** A concrete failure supplies n and, when shapes agree, a failing i.
Assign active occurrences from the concrete input. Inactive occurrences that
share a represented address receive the same value and occupancy; the rest can
receive absent zero. Equal addresses obey congruence. The encoding then computes
exactly the value, occupancy, and active-order observations. A shape failure
can use all absent zeros, since a common output coordinate is unnecessary.

Conversely, fix a satisfying assignment. If shapes differ, all-absent input
witnesses the failure. Otherwise partition active occurrences by tensor name
and concrete address. Congruence gives one consistent cell per class and
admission guarantees bounds. Materialize these cells and leave all others absent
zero. Every required observation is reproduced. Inactive out-of-bounds occurrences
need not be materialized. Active-prefix positions enumerate each finite ordered
list once, so the order comparison is exact. This constructs a concrete failure.

The solver uses real variables. Fixing all integer and Boolean choices leaves a
finite conjunction of homogeneous rational linear equalities and disequalities.
Equalities define a rational subspace; each disequality removes a proper rational
hyperplane. A rational basis and the infinitude of Q show that a finite union of
proper hyperplanes cannot exhaust that subspace if a real satisfying point
exists. Thus satisfiability over reals implies satisfiability over rationals.
The explicit sparse constructions below give rational witnesses as well. QED.

There are finitely many guards, pairwise address-equality arrangements, occupancy
choices and trace comparisons. Enumerate their truth assignments. Each remaining
integer problem is Presburger arithmetic and each value problem is rational
linear feasibility with disequalities. Deciding these and taking the finite
union decides the bad formula and admission. This proves decidability, not a
polynomial bound or a guarantee that the chosen bounded SMT implementation will
finish every admitted instance. Integer literals and coefficients may be large
in a general finite mathematical input; the delivered schema imposes stricter
encoding bounds.

## 3. Grade existence and attainment

Let T(P,Q) be the atoms true on every legal execution of the admitted pair.
The implications above make T closed. A sound grade G is exactly a closed subset
of T. Hence T is the unique greatest sound grade among these observations.
By Theorem A, conclusive correct decisions of all five bad formulas return exactly
T: include an atom iff its formula is unsatisfiable. A timeout or unknown does
not meet this premise. The implementation's complete_grade flag is conditional
on production mode, admission and five conclusive decisions.

This proves attainment relative to a declared finite observation language. It
is not the strongest arbitrary semantic property or contextual equivalence.
The observation abstraction alone is not an attainment argument. For a set X
of paired executions, alpha(X)=intersection of their true-atom sets, and
gamma(G)={e:G is a subset of obs(e)}. With grades ordered by reverse inclusion,
alpha(X) >=set G iff X is a subset of gamma(G), the standard observational
Galois connection. The order reversal and the separate decision theorem matter.

## 4. Two-stored-cell certificates

Fix an allowed shape and output coordinate. Aggregate active occurrences with
the same tensor identity and concrete address to rows a,b over the union U of
addressed cells. Values are a*x and b*x. Do not discard the separate active-read
sets or lists: zero coefficients still matter to union and order.

**Lemma B (row kernels).** The rational forms a*x and b*x have the same zero set
iff both a=b=0 or b=lambda*a for some nonzero rational lambda. If their zero sets
differ, a witness needs at most two nonzero coordinates.

**Proof.** The forward examples have identical zero sets. Otherwise, any coordinate
whose coefficient is zero in exactly one row gives a separating unit vector.
This includes the case of exactly one zero row. If no such coordinate exists,
the coefficient supports are equal and nonempty. Equal supported ratios b_j/a_j
make the rows nonzero proportional. Unequal ratios give j,k with
 a_j*b_k-a_k*b_j != 0.
Set x_j=a_k, x_k=-a_j and all other coordinates zero. Then a*x=0 whereas
b*x=b_j*a_k-b_k*a_j !=0. This proves both directions and the sparse bound. QED.

**Theorem C.** Every failed observation of an admitted pair has a legal witness
with at most two stored input cells, and two is necessary in general for Z.

**Proof.** A shape failure uses no cells. At equal shapes, an order failure
also uses no cells, because potential-term order depends only on n and i.
For unequal values, a unit vector at a differing coefficient uses one stored
cell. For unequal zero-support, Lemma B uses at most two.

For occupancy at the selected coordinate, the predicates are: true for dense;
false for empty and an empty union; an OR over a finite active-cell set for a
nonempty union; and a*x !=0 for compact. Compare all policy pairs. Exactly one
dense side is distinguished by no stored cells. Two unions with different sets
are distinguished by one zero-valued stored cell in their symmetric difference.
Nonempty union versus compact or false is distinguished by a zero-valued stored
cell in the union's set. Two compact predicates reduce to Lemma B. Compact versus
false differs only for a nonzero row and is distinguished by a unit cell at a
nonzero coefficient. Equal constants do not differ. These exhaust the cases.

For tightness, the rows (1,1) and (1,2) on two distinct cells have the same zero
status on every input with zero or one stored cell. With a single cell its value
is either zero on both sides or multiplied by nonzero coefficients on both sides.
The two-cell input (1,-1) gives outputs 0 and -1. Thus two stored cells are
necessary for this Z failure. QED.

With at most 32 source coefficients per row, each having normalized numerator
magnitude and positive denominator below 2^16, a common denominator is below
2^512 and the numerator magnitude is below 32*2^512=2^517. Row normalization
cannot enlarge these bounds. The two-cell construction uses row coefficients
as values. This controls the payload of values; it does not bound the selected
shape or coordinate or the effort of finding them.

The constructor recomputes rows at the solver-selected shape rather than reusing
the solver's rational values. The checker reads the resulting cells, enforces
precondition and concrete bounds and evaluates both observations directly. Its
success is a finite refutation of the supplied IR. It is not global admission,
a proof of an UNSAT answer, or certification of a raw source mapping.

## 5. Revision chains

**Proposition D.** Under one common input interface and precondition,
T(P,R) contains T(P,Q) intersect T(Q,R) for admitted P,Q,R.

**Proof.** Fix an atom in the intersection and any legal input. The observations
of P and Q agree and those of Q and R agree. Equality is transitive, including
shape and list equality, so P and R agree. Quantify over inputs. QED.

This bound can be strict: x -> 2x -> x loses V at both edges and regains it
between endpoints. It is not a consumer-substitution theorem. The producer
change (x0,x1) -> (x0,2*x1) preserves Z, but sum changes 0 to -1 at (1,-1).

## 6. Linear consumers and compatibility

Let U,I be finite input and output sets, C a rational I-by-U matrix, and D a
diagonal matrix with every d_u nonzero. Let R on U be reflexive and symmetric.
Legal masks are exactly all cliques K of R; every rational assignment on K is
legal, with absent zero elsewhere. Explicitly stored zeros are permitted. These
are assumptions on the consumer input space, not physical sparse-format claims.

**Theorem E (support coherence).** supp(Cx)=supp(CDx) for all legal inputs iff,
for every i,u,v, R(u,v) and C_iu !=0 and C_iv !=0 imply d_u=d_v.

**Proof of sufficiency.** Fix K and a row i. If it has no nonzero coefficient in
K, both outputs are zero. Otherwise choose a contributing u0. Since K is a clique,
every other contributing u is compatible with u0. The premise gives one common
nonzero scale lambda on that row's contributing cells. Therefore
(CDx)_i=lambda*(Cx)_i, and their zero status agrees. This holds for every row.

**Proof of necessity.** A violating triple i,u,v has u!=v, compatible cells,
nonzero weights and distinct scales. Reflexivity and symmetry make {u,v} legal.
Choose x_u=C_iv, x_v=-C_iu and no other stored cells. The original row is zero;
the changed row is C_iu*C_iv*(d_u-d_v), which is nonzero. Free assignability makes
this a legal witness. Hence support differs. QED.

**Corollary F.** Define an undirected graph on U with edge u--v for distinct
compatible cells that share a row with two nonzero coefficients. Safe nonzero
scales are exactly the functions constant on each connected component. The
components are the finest partition admitting arbitrary independent nonzero
scales for its blocks.

**Proof.** Theorem E asks for equality along each edge. Equality propagates along
paths, and componentwise constancy gives equality on all edges. If a partition
splits a component, a connecting path has an edge across two blocks. Giving those
blocks different scales violates Theorem E. Thus any safe independent-block
partition must keep each component within one block. QED.

Examples: a global sum under unrestricted compatibility has one component on
nonzero weights; an identity consumer has no edges; a zero consumer imposes no
scale restriction; single-cell-only occupancy R(u,v)=(u=v) has no edges even for
a global sum. Two disjoint sum rows give two independently scalable components.

The implementation describes rank-one extents by affine expressions, weights and
scales by total disjoint affine-guard partitions with constant rational values,
and compatibility by an affine Boolean relation. It verifies admission and asks
for the existence of n,i,u,v violating Theorem E. This is a finite symbolic
formula for all admitted shapes, without unrolling a reduction. It validates a
given scale function, not a symbolic synthesis of graph components.

**Essential boundary.** For the producer image {(t,t):t in Q}, C=(1,1) and
D=diag(1,2), outputs are 2t and 3t and always share their zero status, although
Theorem E's edge equality fails. The cancelling witness is outside the image.
The condition remains sufficient for restricted images but is not necessary.
No result here grades arbitrary correlated producers or nonlinear consumers.

## 7. Precisely quantified finite-test limitation

For the mathematical family admitting arbitrary integer thresholds B, let P be
identity and Q_B be identity when n<=B and twice identity otherwise. Any finite
example suite has a maximum tested n; choose B at least that maximum and at least
one. P and Q_B agree on the suite, but differ on a unit input at n=B+1. No finite
example-only suite separates identity from every member of that unbounded family.

Do NOT apply that universal statement to the delivered bounded text/literal
schema. Its finite semantic syntax gives a finite hypothesis class. Choose one
finite distinguishing input for each semantically distinct pair and take their
finite union: a finite distinguishing suite exists, although it may be impractical.
The retained B=32 example only demonstrates a particular finite suite's miss.
This standard limitation argument is not a claim of research novelty.

## 8. What is and is not proved

The arguments establish the stated mathematics; the code executes finite checks
and trusted-solver queries. They do not prove a verified parser, correct Z3,
correct native ABI behavior on every platform, correctness of a repository-to-IR
mapping, IEEE floating-point equivalence, alias safety, physical sparse-format
properties, full reduction equivalence, novelty, or public-patch effectiveness.
The separate implementation paths check finite instances; they do not replace
the written arguments or verify the implementations formally.

## 9. Public source-adapter equivalence

The public study does not parse arbitrary Python or C++. A commit is admitted
only when every changed production hunk has a fixed parent/child source locator,
a source-derived invariant, a complete observable, an independent before/after
model, a universal argument, and an unchanged-downstream congruence. The exact
hunk disposition is frozen in `data/public-adapter-evidence.json`. Bounded
execution validates the models; it does not replace the source argument.

**Proposition G (P01 admission failure).** The P01 parent and child construction
regions are not equivalent on all source-reachable inputs satisfying the actual
source assertion.

**Proof.** The source asserts only that the global index-variable dictionary is
nonempty. Consider two operands, the first scalar and the second indexed by
`i`, with indexed result `i`. The parent constructs Python source containing
`tensor_vars[0][]`, which raises `SyntaxError`. The child constructs an empty
index tuple and a one-index access directly, producing a CIN multiplication and
assignment. The analogous scalar-second-operand and scalar-result cases also
differ. Therefore per-operand and result non-scalarity cannot be introduced as a
source invariant. The retained one-to-four-operand enumeration establishes only
29,222 equal ASTs in a finite successful domain; it is not a universal source
adapter, so P01 abstains. QED.

**Theorem H (P04 dispatcher extraction).** Under P04's fixed parent LLIR node
invariant, the old monolithic lowerer and the extracted-helper lowerer emit
identical strings and equal persistent comment-suppression state when initialized
with equal state. String dispatch prefixes the entire string once, rather than
indenting each embedded line. A true suppression request sets the flag and a
later false request does not reset it; induction over calls preserves this state.

**Proof.** The parent reference is a monolithic transcription of the fixed
parent file. The child reference separately implements expression, loop,
conditional, and function helpers; no changed conditional or loop logic is
shared between the two paths. Perform case analysis on every parent dispatcher
variant. Primitive cases use the same literal punctuation and indentation. For
recursive cases, assume proper children emit equal strings and substitute them
into the unchanged surrounding format. The condition-list proof includes simple
conditionals, explicit else bodies, `make_last_case_else=True`, and both present
and absent `ForLoop.init`. Comment suppression, blank lines, list order, and the
fallback remain top-level identity cases. Hence the complete generated strings
are equal. Target-only negative controls that change a condition, drop an else,
or remove a closing brace distinguish the paths, showing that the bounded check
does not pass merely because of a shared renderer. QED.

**Theorem I (P06 full state transition).** Under P06's fixed coordinate-resolver
invariant, the original routine and the extracted five-helper routine return
equal complete ordered LLIR node sequences and leave equal ordered pending maps.
For every finite sequence of calls with equal initial maps and equal intervening
inputs, both the returned sequence and post-map agree after every call.

**Proof.** The first four blocks (iterator loads, coordinate choice, compressed
assembly, coordinate ends) preserve every predicate, iterator order, constructor
field and the unchanged map. The dense block is a transition on the lowerer's
`dense_coord_resolve_stmt_to_dep_index_vars`, not a pure output template.

Let E be the ordered pre-map of declaration/dependency-list pairs, T the offered
dense iterators, and F the snapshot set of defined IndexVars. IndexVar equality
and hashing in fixed `cin.py` are by name, so name tokens faithfully implement F
and dependency membership. Well-formed LLIR keys and dependency lists remain
stable during the call. The map starts empty in `CINLowerer.__init__` and the
resolver is its insertion/removal site; insertion by name preserves uniqueness
of destination names from that initial state. There is no helper-local reset.

Induct over T. If the LLIR value is absent, both paths skip the iterator (a
Literal node holding zero is present). Otherwise they construct the same VarInit
and read the names of all currently pending declarations. If the destination
name occurs, both leave its old statement, payload and map position unchanged.
Otherwise both append the new declaration and its dependency list. This test
occurs before any readiness scan: a ready old entry still suppresses a new one.
The resulting ordered snapshot E+ is therefore equal.

Induct over E+. Both use set(dependencies) subset F as readiness, ignoring repeated
names but preserving the original dependency list as state payload. A ready entry
is emitted and removed by its exact key; an unready entry remains unchanged.
Emission does not add a new defined IndexVar, and the fixed F cannot cascade.
Consequently the emitted list is the same stable ready subsequence and the
post-map is the same stable unready subsequence. Both emit the dense comment
exactly when the ready subsequence is nonempty. The caller concatenates all five
blocks in parent order, proving full returned-node and map equality.

For call-sequence induction, the initial maps agree. The single-call result gives
equal post-maps, which become the next pre-maps. The unchanged caller supplies
equal next iterator/defined-variable inputs, so the induction repeats. The same
argument accommodates additional defined IndexVars between calls without inventing
definitions during a scan. This proves the finite-sequence statement universally,
not just for the retained grid.

The adapter's `CoordResult` compares full node fields and ordered map entries;
`DenseTransition` additionally records pre/scan/post state, insertion/skip and
retain flags. The independent `dense_effects.py` reference interprets these
operations on ordered lists and never calls either changed adapter path. All
400 frozen single-call cases pass effect replay. Eight additional sequences
cover 22 calls, and three output-preserving state-only mutations are rejected.
These finite source-effect certificates are separate from the two-cell theorem
and the 18-mutant denominator. A negative control changes the coordinate end from
`pX1_end = pX0 + 1` to `+2` while preserving the top-level node-kind signature;
full-node comparison rejects it, so label equality is not used as evidence.
QED.

**Theorem J (P08 fixed-production truthiness cascade).** For every direct
`TensorVar` construction in the fixed P08 child production tree, the parent and
child mode-order initializers return the same list.

**Proof.** The immutable child-tree inventory shows that direct production
constructors in `ops.py`, `stensor.py`, and `cin_lowerer.py` pass a format; many
also pass shape or mode order. `Workspace.__init__` sets `dim` and `dense` before
calling `TensorVar.__init__`, and its overridden `format` property supplies a
format object. Thus every fixed production call has at least one of a truthy
explicit order, a truthy shape, or a present format. If the explicit order is
truthy, both implementations select it. Otherwise, if shape is truthy, both
select its identity order. Otherwise both select the identity order of the
present format. These cases follow the same priority. The 96 equivalence-domain
combinations exercise them. Four additional controls with absent format and no
truthy explicit order or shape are executed separately: the parent raises
`AttributeError`, whereas the child returns `None`. They are documented domain
exclusions, not silently filtered successes, and direct external construction in
that excluded domain is not claimed equivalent. QED.

**Corollary K (downstream observation preservation).** Suppose an admitted
adapter's observable is the complete input consumed by an unchanged deterministic
downstream phase, and that phase has no hidden dependence on the replaced source
mechanism. Then equality of the adapter observable implies equality of every
paper observation S, V, Z, M, and O at the phase output.

**Proof.** Equal phase inputs to the same deterministic relation yield equal
phase outputs. Each declared observation is a function of those outputs, so all
five agree. QED.

For P06, that complete phase input is the pair (returned LLIR, ordered post-map),
with other caller/lowerer fields unchanged. It includes the state consumed by
later resolver calls; equality of returned nodes alone does not satisfy G4 or
this corollary. This transition layer does not add mutation to the finite-read
tensor IR or extend Theorems A--F to arbitrary mutable programs.

The corollary is deliberately conditional. It excludes reflection on source
text, timing, direct external calls outside the documented invariant, exception
identity outside the adapter interface, undefined native behavior, changed
downstream files, and omitted source edits. Three of twelve commits pass all
seven gates; nine, including P01, remain abstentions. Development admits one of
four and the later retrospective segment two of eight. These are descriptive
coverage counts, not a blind estimate of a population parameter.
