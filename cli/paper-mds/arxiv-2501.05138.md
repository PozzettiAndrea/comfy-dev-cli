# Preference Queries over Taxonomic Domains

#### Paolo Ciaccia 1

#### Davide Martinenghi 2

#### Riccardo Torlone 3

<sup>1</sup>University of Bologna, Italy, paolo.ciaccia@unibo.it <sup>2</sup>Politecnico di Milano, Italy, davide.martinenghi@polimi.it <sup>3</sup>Universit`a Roma Tre, Italy, torlone@dia.uniroma3.it

#### Abstract

When composing multiple preferences characterizing the most suitable results for a user, several issues may arise. Indeed, preferences can be partially contradictory, suffer from a mismatch with the level of detail of the actual data, and even lack natural properties such as transitivity. In this paper we formally investigate the problem of retrieving the best results complying with multiple preferences expressed in a logic-based language. Data are stored in relational tables with taxonomic domains, which allow the specification of preferences also over values that are more generic than those in the database. In this framework, we introduce two operators that rewrite preferences for enforcing the important properties of transitivity, which guarantees soundness of the result, and specificity, which solves all conflicts among preferences. Although, as we show, these two properties cannot be fully achieved together, we use our operators to identify the only two alternatives that ensure transitivity and minimize the residual conflicts. Building on this finding, we devise a technique, based on an original heuristics, for selecting the best results according to the two possible alternatives. We finally show, with a number of experiments over both synthetic and real-world datasets, the effectiveness and practical feasibility of the overall approach.

## 1 Introduction

Preferences strongly influence decision making and, for this reason, their collection and exploitation are considered building blocks of content-based filtering techniques [\[12,](#page-30-0) [69,](#page-36-0) [68\]](#page-36-1). A key issue in this context is the mismatch that usually lies between preferences and data, which often makes it hard to recommend items to customers [\[50\]](#page-34-0). Indeed, whether they are collected by tracing the actions of the users or directly elicited from them, preferences are typically expressed in generic terms (e.g., I prefer pasta to beef), whereas available data is more specific (the menu might contain lasagne and hamburger). The problem of automatically suggesting the best solutions becomes even more involved when several preferences at different levels of granularity and possibly conflicting with each other are specified, as shown in the following example that will be used throughout the rest of the paper.

<span id="page-1-1"></span>Example 1. We would like to select some bottles of wine from the list in Figure [1](#page-1-0) available in an e-commerce store. We prefer white wines to red ones, yet we prefer Amarone (a famous red wine) to white wine. For the producer, we prefer Tuscan wineries located in the province of Siena to those in the Piedmont province of Asti. Moreover, if the winery lies in the Langhe wine region (which spans different provinces, partially including, among others, Asti and Cuneo) we prefer an aged wine (i.e., produced before 2017) to a more recent one. Finally, we would like to have suggestions only for the "best" possible alternatives.

<span id="page-1-0"></span>

| Wines    |             |      |   |  |
|----------|-------------|------|---|--|
| Wine     | Winery      | Year |   |  |
| Arneis   | Correggia   | 2019 | a |  |
| Amarone  | Masi        | 2014 | b |  |
| Amarone  | Bertani     | 2013 | c |  |
| Canaiolo | Montenidoli | 2015 | d |  |
| Barolo   | Laficaia    | 2014 | e |  |
| Arneis   | Ceretto     | 2019 | f |  |

Figure 1: A list of wines

We first observe that further information is needed in this example to identify the solutions that better fit all the mentioned preferences. For instance, we need to know the province and the wine region in which all the wineries are located. In addition, the example shows that there are two important issues that need to be addressed in such scenarios. First, conflicts can occur when preferences are defined at different levels of detail. Indeed, the preference for Amarone, which is a red wine, is in contrast with the more generic preference for white wines. Second, further preferences can be naturally derived from those that are stated explicitly. For instance, from the preference for wines from Siena to those from Asti and the preference for aged wines when they are from the Langhe region, we can also derive, by transitivity, a preference for wines from Siena to young wines from Langhe.

In this paper we address the problem of finding the best data stored in a repository in a very general scenario in which, as in the above example: (i) preferences may not match the level of detail of the available data, (ii) there may be conflicts between different preferences, and (iii) known preferences can imply others. Specifically, unlike previous approaches that have only tackled the problem of mapping preferences to data (see, e.g., [\[53\]](#page-34-1)), we formally investigate the two main principles that need to be taken into account in this context: specificity and transitivity. Specificity is a fundamental tool for resolving conflicts between preferences by giving precedence to the most specific ones, as it is natural in practical applications. For instance, in our example, the specific preference for Amarone over white wines counts more than the generic preference for white wines over red ones. The specificity principle is indeed a pillar of non-monotonic reasoning, where a conclusion derived from a more specific antecedent overrides a conflicting inference based on a less specific antecedent [\[43\]](#page-33-0). On the other hand, transitivity, besides being a natural property, is important also from a practical point of view, since non-transitive preferences might induce cycles, a fact that could make it impossible to identify the best solutions [\[12\]](#page-30-0).

To tackle the problem of dealing with non-monotonic preferences, we rely on a natural extension of the relational model in which we just assume that taxonomies, represented by partial orders on values, are defined on some attribute domains [\[60\]](#page-35-0). Thus, for instance, in a geographical domain we can establish that the value Italy is more generic than the value Rome, since the former precedes the latter in the partial order. We then call t-relations (i.e., relations over taxonomies) standard relations involving attributes over these taxonomic domains.

We express preferences in this model in a declarative way, by means of firstorder preference formulas specifying the conditions under which, in a t-relation, a tuple t<sup>1</sup> is preferable to a tuple t2. By taking advantage of the taxonomies defined over the domains, in a preference formula we can refer to values that are more generic than those occurring explicitly in a t-relation (e.g., the fact that we prefer white to red wines, as in Example [1\)](#page-1-1). When evaluated over a t-relation r, a preference formula returns a preference relation that includes all the pairs of tuples (t1, t2) in r such that t<sup>1</sup> is preferable to t2. Since the input preference formula may not induce a preference relation enjoying both transitivity and specificity, such a formula then needs to be suitably rewritten. Eventually, the rewritten formula is used to select the best tuples in r by means of the Best operator, which filters out all the tuples that are strictly worse than some other tuple [\[24\]](#page-31-0). How this rewriting has to be performed is thus the main focus of this paper.

Problem. To study, from both a theoretical and a practical point of view, to which extent the properties of transitivity and specificity can be obtained by suitable rewritings of the initial preference formula.

We tackle the problem by introducing and formally investigating two operators that rewrite a preference formula: T to enforce transitivity and S to remove all conflicts between more generic and more specific preferences, thus attaining specificity. In order to try to guarantee both properties, one thus needs to use both operators. The first natural question that arises is whether the order in which they are applied is immaterial. Unfortunately, it turns out that these two operators do not commute. More so, even their repeated application can produce different results, inducing incomparable preference relations. This motivates us to explore the (infinite) space of possible sequences of such operators. Based on this analysis, we prove that it is indeed impossible to always guarantee at the same time transitivity of the obtained preference relation and a complete absence of conflicts therein, no matter the order in which T and S are considered and how many times they are applied. Intuitively, the removal of conflicts may compromise transitivity, whereas enforcement of transitivity may (re-)introduce conflicts. We also show that this impossibility result would persist even if one considered a more fine-grained S operator that removes conflicts one by one (instead of all at a time). In spite of this intrinsic limitation, we formally show that: (i) the set of all possible sequences of operators can be reduced to a finite (and small) set, and (ii) there are only two sequences, which we call minimal-transitive, that guarantee transitivity and, at the same time, minimize residual conflicts between preferences. We also show that the application of the Best operator using the rewritten formulas obtained through the two minimal-transitive sequences can lead to very different results. However, in common practical cases, experimental evidence shows that one of the two sequences typically resolves more conflicts, thus returning a more refined set of best tuples.

In order to observe and assess the actual behavior of sequences of operators, we developed an engine for implementing our approach, which rewrites an input preference formula and evaluates it over t-relations. We conducted a number of experiments over both synthetic and real-world data and taxonomies in scenarios of different complexities, showing that: (i) the overhead incurred by the rewriting process is low for the considered sequences; (ii) the computation of the best results largely benefits from the minimization of conflicts between preferences, both in terms of execution time and cardinality of results; (iii) the adoption of an original heuristic sorting criterion based on taxonomic knowledge greatly reduces execution times.

In sum, the contributions of this paper are the following:

- a general framework that is able to express, in a logic-based language, preferences over relations with taxonomic domains, as illustrated in Section [2;](#page-4-0)
- two operators, presented in Section [3,](#page-7-0) that rewrite, within this framework, the input preferences so as to enforce the important properties of transitivity, which is required for the correctness of the result, and specificity, which solves possible conflicts among preferences;
- the formal investigation, illustrated in Section [4,](#page-12-0) of the combined and repeated application of these operators to an initial set of preferences;
- a technique based on an original heuristics, presented in Section [5,](#page-17-0) for selecting the best results associated with given sequences of operators, and the characterization of their differences;
- the experimentation of the overall approach over both synthetic and realworld data, showing its effectiveness and practical feasibility, as illustrated in Section [6.](#page-19-0)

Related works are reported in Section [7](#page-26-0) whereas some conclusions are sketched in Section [8.](#page-29-0)

This paper is an extended version of [\[25\]](#page-31-1), with formal proofs available in the appendix.

## <span id="page-4-0"></span>2 Preliminaries

In this section, we introduce our data model, originating from [\[60\]](#page-35-0), and a logicbased preference model, inspired by [\[12\]](#page-30-0).

We remind that a partial order ≤ on a domain V is a subset of V ×V , whose elements are denoted by v<sup>1</sup> ≤ v2, that is: 1) reflexive (v ≤ v for all v ∈ V ), 2) antisymmetric (if v<sup>1</sup> ≤ v<sup>2</sup> and v<sup>2</sup> ≤ v<sup>1</sup> then v<sup>1</sup> = v2), and 3) transitive (if v<sup>1</sup> ≤ v<sup>2</sup> and v<sup>2</sup> ≤ v<sup>3</sup> then v<sup>1</sup> ≤ v3). A set with a partial order is called a poset.

### 2.1 Data Model

We consider a simple extension of the relational model in which the values of an attribute can be arranged in a hierarchical taxonomy.

Definition 1 (Taxonomy). A taxonomy is a poset T = (V, ≤<sup>V</sup> ), where V is a set of values and ≤<sup>V</sup> is a partial order on V .

Example 2. A taxonomy relevant to our working example represents production sites at different levels of granularity. Considering Example [1,](#page-1-1) this taxonomy, Tp, shown in Figure [2a,](#page-5-0) includes values representing wineries (as minimal elements of the poset) as well as values representing provinces, wine regions, and regions of Italy. For instance, we can have values like Laficaia (a winery), Cuneo (a province), Langhe (a wine region) and Piedmont (a region of Italy), with Laficaia ≤<sup>V</sup> Cuneo, Laficaia ≤<sup>V</sup> Langhe, Laficaia ≤<sup>V</sup> Piedmont, Cuneo ≤<sup>V</sup> Piedmont, and Langhe ≤<sup>V</sup> Piedmont. Additionally, Figure [2b](#page-5-1) shows a simple taxonomy T<sup>w</sup> for wines, which associates each wine with a corresponding color. Finally, we assume a taxonomy T<sup>y</sup> mapping production years before 2017 to aged and the other years to young.

A t-relation is a standard relation of the relational model defined over a collection of taxonomies.

Definition 2 (t-relation, t-schema, t-tuple). A t-schema is a set S = {A<sup>1</sup> : T1, . . . , A<sup>d</sup> : Td}, where each A<sup>i</sup> is a distinct attribute name and each T<sup>i</sup> = (V<sup>i</sup> , ≤<sup>V</sup><sup>i</sup> ) is a taxonomy. A t-relation over S is a set of tuples over S ( t-tuples) mapping each A<sup>i</sup> to a value in Vi. We denote by t[A<sup>i</sup> ] the restriction of a t-tuple t to the attribute Ai.

For the sake of simplicity, in the following we will not make any distinction between the name of an attribute of a t-relation and that of the corresponding taxonomy, when no ambiguities can arise. We observe that our model also accommodates "standard" attributes, in which the domain V is a set of flat values (i.e., ≤<sup>V</sup> is empty).

<span id="page-5-0"></span>![](_page_5_Figure_0.jpeg)

(a) A taxonomy Tp for production sites.

![](_page_5_Figure_2.jpeg)

(b) A taxonomy Tw for wines.

<span id="page-5-1"></span>Figure 2: Taxonomies for the running example.

Example 3. A catalog of Italian wines can be represented by the t-schema S = {Wine : Tw, Winery : Tp, Year : Ty}. A possible t-relation over S is shown in Figure [1.](#page-1-0) Then we have b[Year] = 2014 and e[Wine] = Barolo.

### <span id="page-5-2"></span>2.2 Preference Model

Given a set of attribute-taxonomy pairs A<sup>1</sup> : T1, . . . , A<sup>d</sup> : Td, in which A1, . . . , A<sup>d</sup> are all distinct, let T denote the set of all possible t-tuples over any t-schema that can be defined using such pairs.

Definition 3 (Preference relation). A preference relation over the t-tuples in T is a relation ⪰ on T × T . Given two t-tuples t<sup>1</sup> and t<sup>2</sup> in T , if t<sup>1</sup> ⪰ t<sup>2</sup> then t<sup>1</sup> is (weakly) preferable to t2, also written as (t1, t2) ∈ ⪰. If t<sup>1</sup> ⪰ t<sup>2</sup> but t<sup>2</sup> ̸⪰ t1, then t<sup>1</sup> is strictly preferable to t2, denoted by t<sup>1</sup> ≻ t2.

Definition 4 (Incomparability and Indifference). Given a preference relation on T and a pair of t-tuples t<sup>1</sup> and t<sup>2</sup> in T , if neither t<sup>1</sup> ⪰ t<sup>2</sup> nor t<sup>2</sup> ⪰ t1, then t<sup>1</sup> and t<sup>2</sup> are incomparable. When both t<sup>1</sup> ⪰ t<sup>2</sup> and t<sup>2</sup> ⪰ t<sup>1</sup> hold, t<sup>1</sup> and t<sup>2</sup> are indifferent, denoted by t<sup>1</sup> ≈ t2.

Notice that if ⪰ is transitive, then ≈ is an equivalence relation (up to reflexivity) and ≻ is a strict partial order (i.e., transitive and irreflexive). These properties do not hold, in the general case, when ⪰ is not transitive.

The transitivity of ⪰ implies that all the t-tuples involved in a cycle are indifferent to each other, thus the cycle vanishes when strict preferences are considered.

Example 4. Let us consider the t-relation in Figure [1](#page-1-0) and assume that we have the cycle of preferences: a ⪰ b, b ⪰ c, and c ⪰ a. If ⪰ is transitive then we also have a ⪰ c (from a ⪰ b and b ⪰ c), b ⪰ a (from b ⪰ c and c ⪰ a) and c ⪰ b (from c ⪰ a and a ⪰ b). Then, since a ≈ b, b ≈ c, and a ≈ c, no cycle is present in ≻.

Given a set of t-tuples r ⊆ T , the "best" t-tuples in r according to the preference relation ⪰ can be selected by means of the Best operator β [\[24\]](#page-31-0), which returns the t-tuples t<sup>1</sup> of r such that there is no other t-tuple t<sup>2</sup> in r that is strictly preferable to t1.

Definition 5 (Best operator). Given a t-relation r and a preference relation ⪰ on the t-tuples in r, the best operator β is defined as follows: β≻(r) = {t<sup>1</sup> ∈ r | ∄t<sup>2</sup> ∈ r, t<sup>2</sup> ≻ t1}.

When ≻ is a strict partial order, β≻(r) is not empty for any non-empty trelation r. We remind that, if ≻<sup>1</sup> and ≻<sup>2</sup> are such that ≻1⊆≻<sup>2</sup> then β<sup>≻</sup><sup>2</sup> (r) ⊆ β<sup>≻</sup><sup>1</sup> (r) holds for all r [\[12\]](#page-30-0).

Example 5. Let us consider the t-relation in Figure [1](#page-1-0) and assume that: b ⪰ a, a ⪰ f, b ⪰ f, b ⪰ d, c ⪰ e, e ⪰ c. It follows that: b ≻ a, a ≻ f, b ≻ f, b ≻ d (since the opposite does not hold for those four preferences), but c ≈ e (since both c ⪰ e and e ⪰ c). Then, we have β≻(r) = {b, c, e}.

For expressing preferences we consider a logic-based language, in which t<sup>1</sup> ⪰ t<sup>2</sup> iff they satisfy the first-order preference formula F(t1, t2): t<sup>1</sup> ⪰ t<sup>2</sup> ⇔ F(t1, t2). Thus, when considering strict preferences we have:

<span id="page-6-0"></span>
$$t_1 \succ t_2 \Leftrightarrow F(t_1, t_2) \land \neg F(t_2, t_1). \tag{1}$$

As in [\[12\]](#page-30-0), we only consider intrinsic preference formulas (ipf's), i.e., firstorder formulas in which only built-in predicates are present and quantifiers are omitted, as in Datalog. Predicates have either the form (x[A<sup>i</sup> ] ≤V<sup>i</sup> v) or (x[A<sup>i</sup> ] ̸≤V<sup>i</sup> v), where A<sup>i</sup> is an attribute defined over taxonomy T<sup>i</sup> = (V<sup>i</sup> , ≤V<sup>i</sup> ), x is a t-tuple variable over t-schemas including A<sup>i</sup> , and v is a value in V<sup>i</sup> . The predicate (x[A<sup>i</sup> ] ≤V<sup>i</sup> v) (resp. (x[A<sup>i</sup> ] ̸≤V<sup>i</sup> v)) holds for a t-tuple t if (t[A<sup>i</sup> ] ≤V<sup>i</sup> v) (resp. (t[A<sup>i</sup> ] ̸≤V<sup>i</sup> v)) holds. For convenience, we get rid of ¬ as needed by transforming ≤<sup>V</sup><sup>i</sup> into ̸≤<sup>V</sup><sup>i</sup> and vice versa.

For the sake of generality, we consider that formula F consists of a set of preference statements, where each statement P<sup>i</sup> is in Disjunctive Normal Form (DNF), each disjunct of P<sup>i</sup> being termed a preference clause, Ci,j :

$$P_i(x,y) = \bigvee_{j=1}^{m_i} C_{i,j}(x,y)$$

and where each clause Ci,j is a conjunction of predicates. We assume that each clause Ci,j is non-contradictory, i.e., ∃t1, t<sup>2</sup> ∈ T such that Ci,j (t1, t2) is true. When a statement consists of a single clause we use the two terms "clause" and "statement" interchangeably.

A formula F is a disjunction of n ≥ 1 preference statements:

$$F(x,y) = \bigvee_{i=1}^{n} P_i(x,y).$$

<span id="page-7-1"></span>Example 6. The preferences informally stated in Example [1](#page-1-1) can be expressed by the formula

$$F(x,y) = P_1(x,y) \lor P_2(x,y) \lor P_3(x,y) \lor P_4(x,y)$$

where the 4 preference statements, in which we use ≤ in place of ≤<sup>V</sup><sup>i</sup> to improve readability, are:

$$\begin{array}{ll} P_1(x,y) = & (x[\mathsf{Wine}] \leq \mathsf{white}) \land (y[\mathsf{Wine}] \leq \mathsf{red}) \\ P_2(x,y) = & (x[\mathsf{Wine}] \leq \mathsf{Amarone}) \land (y[\mathsf{Wine}] \leq \mathsf{white}) \\ P_3(x,y) = & (x[\mathsf{Winery}] \leq \mathsf{Siena}) \land (y[\mathsf{Winery}] \leq \mathsf{Asti}) \\ P_4(x,y) = & (x[\mathsf{Winery}] \leq \mathsf{Langhe}) \land (x[\mathsf{Year}] \leq \mathsf{aged}) \land \\ & (y[\mathsf{Winery}] \leq \mathsf{Langhe}) \land (y[\mathsf{Year}] \leq \mathsf{young}) \end{array}$$

The above statements, when evaluated over the t-tuples in Figure [1,](#page-1-0) yield the following preferences, written as pairs of t-tuples in ⪰ (for the sake of clarity, for each preference we also show the statement used to derive it):

$$\begin{array}{ll} P_1: & (a,b), (a,c), (a,e), (f,b), (f,c), (f,e) \\ P_2: & (b,a), (b,f), (c,a), (c,f) \\ P_4: & (e,f) \end{array}$$

Notice that P<sup>3</sup> yields no preference, since there is no wine from Asti's province in the t-relation in Figure [1.](#page-1-0)

In the rest of the paper, with the aim to simplify the notation, preference statements in the examples will be written with a compact syntax, by omitting variables and attributes' names, and separating with ⪰ the "better" part from the "worse" part. For instance, the above statement P<sup>4</sup> will be written as:

$$P_4 = \mathsf{Langhe} \land \mathsf{aged} \succeq \mathsf{Langhe} \land \mathsf{young}.$$

# <span id="page-7-0"></span>3 Operations on Preferences

In this section we introduce two operators that can be applied to a preference relation, postponing to the next section the detailed analysis of the possible ways in which they can be combined. The two operators are: Transitive closure (T) and Specificity-based refinement (S). Let ⪰ denote the initial preference relation; the resulting relation is indicated ⪰<sup>T</sup> for T and ⪰<sup>S</sup> for S. Multiple application of operators, e.g., first T and then S, leads to the relation (⪰T)S, which we compactly denote as ⪰TS. In general, for any sequence X ∈ {T, S} ∗ ,  $\succeq_{\mathsf{X}}$  is the preference relation obtained from the initial preference relation  $\succeq$  by applying the operators in the order in which they appear in  $\mathsf{X}$ . Notice that  $\succeq_{\varepsilon} = \succeq$ , where  $\varepsilon$  denotes the empty sequence.

We describe the behavior of the two operators by means of suitable rewritings of a preference formula. Given a sequence X of operators, and an initial (input) formula F(x, y) inducing the preference relation  $\succeq$ ,  $F^{\mathsf{X}}(x, y)$  denotes the rewriting of F that accounts for the application of the X sequence, thus yielding  $\succeq_{\mathsf{X}}$ .

#### 3.1 Transitive Closure

Transitivity of  $\succeq$ , and consequently of  $\succ$ , is a basic requirement of any sound preference-based system. If  $\succeq$  is not transitive then  $\succ$  might contain cycles, a fact that could easily lead either to empty or non-stable results, as the following example shows.

<span id="page-8-1"></span><span id="page-8-0"></span>**Example 7.** Consider the t-tuples in Figure 3, in which both Sbarbata and Molinara are rosé wines and Vogadori is a winery in the Valpolicella wine region.

| Wine     | Winery    | Year |        |
|----------|-----------|------|--------|
| Arneis   | Correggia | 2019 | g      |
| Barolo   | Laficaia  | 2014 | h      |
| Sbarbata | Laficaia  | 2019 | $\ell$ |
| Molinara | Vogadori  | 2014 | m      |

Figure 3: A set of wines for Example 7.

From the preference statements in Example 6, we have  $g \succeq h$  (through  $P_1$ ) and  $h \succeq \ell$  (through clause  $P_4$ ). However,  $g \not\succeq \ell$ . Assume now two additional preference statements

```
\begin{array}{ll} P_{\alpha} = & \operatorname{ros\'e} \wedge \operatorname{young} \succeq \operatorname{ros\'e} \wedge \operatorname{aged}, \\ P_{\beta} = & \operatorname{Valpolicella} \succeq \operatorname{Roero}, \end{array}
```

which, respectively, induce preferences  $\ell \succeq m$  and  $m \succeq g$ . Overall, since no other preferences hold, we have the non-transitive cycle of strict preferences  $g \succ h, h \succ \ell, \ell \succ m$  and  $m \succ g$ . So, for a t-relation  $r = \{g, h, \ell, m\}$ , we have  $\beta_{\succ}(r) = \emptyset$ .

Consider now  $r' = \{g, h, \ell\}$ , for which  $\beta_{\succ}(r') = \{g\}$ , and  $r'' = \{g, \ell, m\}$ , for which  $\beta_{\succ}(r'') = \{\ell\}$ . Although both r' and r'' contain g and  $\ell$ , the choice of which of these t-tuples is better than the other depends on the presence of other t-tuples (like h and m), thus making the result of the  $\beta$  operator unstable.

The transitive closure operator, denoted T, given an input preference relation  $\succeq_{\mathsf{X}}$  yields the preference relation  $\succeq_{\mathsf{XT}}$ . We remind that, as observed in Section 2.2, the transitivity of  $\succeq_{\mathsf{XT}}$  entails that of  $\succ_{\mathsf{XT}}$ . The transitive closure  $F^{\mathsf{XT}}$  of an ipf  $F^{\mathsf{X}}$  with n statements  $P_1, \ldots, P_n$  is still a finite ipf that can be

#### **Algorithm 1:** T operator: Transitive closure of $F^{X}$ .

Input: formula  $F^{X} = P_1 \vee \ldots \vee P_n$ , taxonomies  $T_1, \ldots, T_d$ .

Output:  $F^{XT}$ , the transitive closure of  $F^{X}$ .

- 1.  $F^{XT} := F^X$
- <span id="page-9-1"></span>2. repeat
- $3. \quad newPref := \mathbf{false}$
- <span id="page-9-3"></span>4. **for each** ordered pair  $(P_i, P_j)$ ,  $P_i$  in  $F^{XT}$ ,  $P_j$  in  $F^{X}$
- 5. P := emptv
- <span id="page-9-4"></span>6. **for each** ordered pair  $(C_m, C_q)$ ,  $C_m$  in  $P_i$ ,  $C_q$  in  $P_j$
- <span id="page-9-5"></span>7. **if**  $\exists t_1, t_2, t_3 \in \mathcal{T}$  s.t.  $C_m(t_1, t_2) \wedge C_q(t_2, t_3) =$ **true**  $\mathbf{then} \ P := P \vee (C_m^b(x) \wedge C_a^w(y))$
- 8. if  $P \neq \text{empty then } F^{XT} := F^{XT} \vee P, newPref := \text{true}$
- <span id="page-9-2"></span>9. until newPref = false
- <span id="page-9-0"></span>10. return  $F^{XT}$

computed via Algorithm 1, along the lines described in [12]. For the sake of conciseness, given a preference clause C(x,y), we denote by  $C^b(x)$  (resp.  $C^w(y)$ ) the part of C(x,y) given by the conjunction of the predicates involving variable x (resp. y). Notice that  $C(x,y) = C^b(x) \wedge C^w(y)$  holds.

In the main loop of the algorithm (lines (2)–(9)) we test the possibility of transitively combining two preference statements at a time (line (4)), by considering each of their clauses (line (6)). Since clauses are assumed to be noncontradictory, the test at line (7), which can also be written as  $C_m^b(t_1) \wedge C_m^w(t_2) \wedge C_q^b(t_2) \wedge C_q^w(t_3)$ , reduces to checking if  $C_m^w(t_2) \wedge C_q^b(t_2)$  is satisfiable in  $\mathcal{T}$ . This can be done by checking whether no contradictory pair of predicates occurs in  $C_m^w(t_2) \wedge C_q^b(t_2)$ . In particular, two predicates of the form  $(x[A_i] \leq V_i, v_1)$  and  $(x[A_i] \leq V_i, v_2)$ , over the same attribute  $A_i$  and using the same variable x, are contradictory if values  $v_1$  and  $v_2$  are different and have no common descendant in the taxonomy  $V_i$  (Section 6 further discusses how to check the existence of a common descendant). If the predicates are of the form  $(x[A_i] \leq V_i, v_1)$  and  $(x[A_i] \not\leq V_i, v_2)$ , then they are contradictory in case there is a path from  $v_1$  to  $v_2$  in  $V_i$  (or  $v_1 = v_2$ ).

The fact that the transitive closure is computed with respect to the (possibly infinite) domain  $\mathcal{T}$  of the t-tuples, and *not* with respect to a (finite) t-relation r of t-tuples, is quite standard for preference relations (see e.g., [12]), and has the advantage of yielding a relation  $\succeq_{\mathsf{XT}}$  that does not change with r and avoiding the problems discussed in Example 7.

<span id="page-10-1"></span>**Example 8.** Continuing with Example 6, the transitive closure of F is the formula  $F^{\mathsf{T}}$  that, among others, adds the following statements to F:

 $P_5 = \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \$ 

Statement  $P_5(x,y)$  clearly follows from  $P_2(x,z)$  and  $P_1(z,y)$ . More interesting is statement  $P_6(x,y)$ , obtained from  $P_3(x,z)$  and  $P_4(z,y)$ . Since there exists at least one winery that is both in the Asti province and in the Langhe region (Casorzo is one of them), this allows  $P_3(x,z)$  and  $P_4(z,y)$  to be transitively combined. With reference to the t-tuples in Figure 1, we then have  $d \succeq_T f$ .

After applying the T operator, we simplify the formula as needed, and, in particular, we remove statements that are subsumed by other statements. Similarly, we also simplify statements by removing contradictory clauses and clauses subsumed within the same statement.

#### 3.2 Specificity-based Refinement

The most intriguing of our operators is the specificity-based refinement S. As it is also apparent from Example 6, conflicting preferences, such as (a,b) and (b,a), may hold. Although these preferences are compatible with the given definition of preference relation, we argue that some of these conflicts need to be resolved in order to derive a preference relation that better represents the stated user preferences. To this end we resort to a specificity principle, which we adapt from the one typically used in non-monotonic reasoning to solve conflicts. According to such a principle, a conclusion derived from a more specific antecedent overrides a conflicting (defeasible) inference based on a less specific antecedent, that is, more specific information overrides more generic information.

<span id="page-10-2"></span>**Example 9.** In our working example, we have a generic preference for white wines over red wines. With no contradiction with the generic preference, we might have a *more specific* preference stating that a bottle of Amarone (a red wine) is superior to a bottle of Arneis (a white wine). In this case, the more specific preference would entail, among others,  $b \succeq a$ ; yet, because of the more generic preference for white wines, we also have  $a \succeq b$ , thus a and b become indifferent. However, giving the same importance to both preference statements contradicts the intuition, as the more specific preference should take precedence over the more generic one.

The specificity principle we adopt for analyzing conflicting preferences is based on the *extension* of preferences statements, i.e., on the set of pairs of t-tuples in  $\mathcal{T}$  for which a statement is true.

<span id="page-10-0"></span>**Definition 6** (Specificity principle). Let  $\succeq_X$  be a preference relation, and let  $F^X$  be the corresponding formula. Let  $P_i$  and  $P_j$  be two preference statements in  $F^X$ . We say that  $P_i$  is more specific than  $P_j$  if, for any pair of t-tuples  $t_1, t_2 \in \mathcal{T}$ 

such that  $P_i(t_1, t_2)$  is true, then  $P_j(t_2, t_1)$  is also true, and the opposite does not hold

From Definition 6 we can immediately determine how a less specific statement has to be rewritten so as to solve conflicts.

<span id="page-11-1"></span>**Lemma 1.** A preference statement  $P_i(x,y)$  is more specific than  $P_j(y,x)$  iff  $P_i(x,y)$  implies  $P_j(y,x)$  (written  $P_i(x,y) \to P_j(y,x)$ ) and the opposite does not hold. If  $P_j(y,x)$  is replaced by  $P'_j(y,x) = P_j(y,x) \land \neg P_i(x,y)$ , then  $P_i$  and  $P'_j$  do not induce any conflicting preferences.

Checking whether  $P_i(x, y)$  implies  $P_j(y, x)$  amounts to checking whether  $P_i(x, y) \wedge \neg P_j(y, x)$  is false, i.e., every clause in the resulting formula is contradictory (contradictions can be checked as described for T).

The S operator, whose behavior is defined by Algorithm 2, removes from the preferences induced by a formula  $F^{X}$  all those that are conflicting and less specific.

Notice that, after a first analysis of the existing implications among the statements (line (4)) and the rewriting of the implied statements (line (5)), the analysis needs to be repeated, since new implications might arise. For instance, let  $F^{\mathsf{X}} = P_1 \vee P_2 \vee P_3$ , with  $P_1(y,x) \to P_2(x,y)$  being the only implication. After rewriting  $P_2(x,y)$  into  $P_2'(x,y) = P_2(x,y) \wedge \neg P_1(y,x)$ , it might be the case that  $P_2'(x,y) \to P_3(y,x)$ , thus  $P_3$  needs to be rewritten.

Although multiple rounds might be needed, Algorithm 2 is guaranteed to terminate. Indeed, if  $P_i(x,y) \to P_j(y,x)$ , and  $P_j(y,x)$  is consequently replaced by  $P'_j(y,x) = P_j(y,x) \land \neg P_i(x,y)$ , the two statements  $P_i$  and  $P'_j$ , as well as their possible further rewritings, have disjoint extensions, and therefore will not interact anymore in the rewriting process. Since the number of statements is finite, so is the number of rewritings, which ensures that the algorithm will eventually stop.

Here too, we simplify the formula resulting from the rewritings according to the same principles used for the  $\mathsf{T}$  operator.

**Example 10.** Continuing with Example 8, the application of the S operator amounts to rewriting formula  $F^{\mathsf{T}}$  by replacing the clause  $P_1(x,y)$  with  $P_1(x,y) \land \neg P_2(y,x)$ , since  $P_2(y,x) \to P_1(x,y)$ . This, after distributing  $\neg$  over the two predicates in  $P_2$  and simplifying, leads to the new clause:

$$P_7 = \text{ white } \succeq_{\mathsf{TS}} \mathsf{red} \land \neg \mathsf{Amarone}.$$

The preferences that were derived from  $P_1$  can be seen in Example 6; we repeat them for the sake of clarity:

$$P_1: (a,b), (a,c), (a,e), (f,b), (f,c), (f,e).$$

Among them, (a, b), (a, c), (f, b), and (f, c) do not satisfy  $P_7(x, y)$ , since both b and c refer to Amarone. Thus,  $P_7: (a, e), (f, e)$ .

<span id="page-11-0"></span><sup>&</sup>lt;sup>1</sup>The hypothesis that  $P_j(y, x)$  does not imply  $P_i(x, y)$  excludes the case of *opposite preference statements* (e.g., white is better than red, and red is better than white), to which the S operator clearly does not apply.

#### **Algorithm 2:** S operator: Specificity-based refinement of $F^{X}$ .

Input: formula  $F^{X} = P_1 \vee ... \vee P_n$ , taxonomies  $T_1, ..., T_d$ .

Output:  $F^{XS}$ , the specificity-based refinement of  $F^{X}$ .

- 1. repeat
- $2. \quad newRound := false$
- 3. **for each** statement  $P_i$
- <span id="page-12-2"></span>4.  $Impl(P_i) := \{P_j | P_j(y, x) \rightarrow P_i(x, y) \land P_i(x, y) \not\rightarrow P_j(y, x)\}$
- <span id="page-12-3"></span>5. if  $Impl(P_i) \neq \emptyset$  then

$$newRound := \mathbf{true}, P_i' := P_i$$

for each  $P_j \in Impl(P_i)$ 

$$P'_i(x,y) := P'_i(x,y) \wedge \neg P_i(y,x)$$

- 6. **if** newRound **then**  $P_i := P'_i, i = 1, ..., n$
- 7. until newRound = false
- <span id="page-12-1"></span>8. return  $F^{XS} = P_i \vee \ldots \vee P_n$

It is relevant to observe that the application of the S operator always leads to smaller (i.e., cleaner) results. For instance, considering t-relation r in Figure 1 and input preference statements  $P_1$  and  $P_2$  from Example 6, we have  $\beta_{\succ}(r) = \{a, b, c, d, f\}$ , whereas  $\beta_{\succ}(r) = \{b, c, d\}$ .

**Lemma 2.** For any t-relation r and any preference relation  $\succeq_{\mathsf{X}}$  we have  $\beta_{\succ_{\mathsf{XS}}}(r) \subseteq \beta_{\succ_{\mathsf{X}}}(r)$ .

# <span id="page-12-0"></span>4 Minimal-Transitive Sequences

In this section we analyze the effect of performing the operations described in the previous section, and prove some fundamental properties of the obtained preference relations. After introducing the basic properties and main desiderata in Section 4.1, we explore the space of possible sequences in Section 4.2 and, as a major result, we show that, out of infinitely many candidates, only a finite number of sequences needs to be considered. Finally, in Section 4.3 we identify the only two sequences that meet all our requirements.

#### <span id="page-12-4"></span>4.1 Basic properties

In order to clarify the relationships between the results of the different operations, we introduce the notions of equivalence and containment between se-

quences of operators.

Definition 7 (Equivalence and containment). Let X, Y ∈ {T, S} ∗ ; X is contained in Y, denoted X ⊑ Y, if for every initial preference relation ⪰, ⪰X⊆⪰Y; X and Y are equivalent, denoted X ≡ Y, if both X ⊑ Y and Y ⊑ X.

Among the basic properties of our operators, we observe that T and S are idempotent, T is monotone and cannot remove preferences, while S cannot add preferences. In addition, the preference relation obtained after applying T on the initial preference relation ⪰ is maximal, in that it includes all other relations obtained from ⪰ by applying T and S in any way.

Theorem 1. Let X, Y ∈ {T, S} ∗ , with X ⊑ Y. Then:

$$\begin{array}{llllllllllllllllllllllllllllllllllll$$

We now focus on those sequences, that we call complete, that include both T and S, since their corresponding operations are both part of the our requirements. In particular, transitivity of the obtained strict preference relation is at the core of the computation of the Best (β) operator, as shown in Example [9.](#page-10-2) To this end, we characterize as transitive those sequences that entail such a transitivity.

Definition 8 (Complete and transitive sequence). A sequence X ∈ {T, S} ∗ is complete if X contains both T and S; X is transitive if, for every initial preference relation ⪰, ≻<sup>X</sup> is transitive.

Eventually, our goal is to drop conflicting and less specific preferences while preserving transitivity. To this end, we add minimality with respect to ⊑ as a desideratum. In particular, we want to determine the so-called minimaltransitive sequences, i.e., those that are minimal among the transitive sequences. As it turns out, all such sequences are also complete.

Definition 9 (Minimal-transitive sequence). Let Σ be a set of sequences; X ∈ Σ is minimal in Σ if there exists no other sequence Y ∈ Σ, Y ̸≡ X such that Y ⊑ X. A minimal-transitive sequence is a sequence that is minimal in the set of transitive sequences.

### <span id="page-13-0"></span>4.2 The space of possible sequences

We now chart the space of possible sequences so as to understand the interplay between completeness, transitivity and minimality.

We start by observing that any sequence with consecutive repetitions of the same operator is equivalent, through idempotence, to a shorter sequence with no such repetitions; for instance, TSS is equivalent to TS. Since sequences with repetitions play no significant role in our analysis, we shall henceforth disregard them.

Clearly, every sequence is contained in T, due to its maximality. Other containment relationships follow from inflation of T and deflation of S. Further relationships come from the following result, stating that adding ST (i.e., removing conflicts and then transitively closing the resulting preference formula) to a sequence ending with T cannot introduce any new preference.

<span id="page-14-1"></span>Lemma 3. Let X ∈ {T, S} ∗ . Then XTST ⊑ XT.

Lemma [3](#page-14-1) induces two chains of inclusions, namely:

<span id="page-14-3"></span><span id="page-14-2"></span>
$$\dots \sqsubseteq \mathsf{TSTST} \sqsubseteq \mathsf{TST} \sqsubseteq \mathsf{T}$$
 (6)

$$\dots \sqsubseteq \mathsf{STSTST} \sqsubseteq \mathsf{STST} \sqsubseteq \mathsf{ST}.$$
 (7)

In addition to that, the following result seems to suggest that the longer sequences in the above chains are preferable, since they lead to larger sets of strict preferences (≻), which, as was observed in Section [2.2,](#page-5-2) correspond to smaller (i.e., cleaner) results for the Best β operator.

Proposition 1. Let X ∈ {T, S} ∗ . Then, for any initial preference relation ⪰, we have ≻XT⊆≻XTST.

There are, evidently, infinitely many sequences in the chains [\(6\)](#page-14-2) and [\(7\)](#page-14-3) and, more generally, in {T, S} ∗ . However, for any given initial preference formula, a counting argument on the number of formulas obtainable through the operators allows us to restrict to only a finite amount of sequences. Moreover, it turns out that the repeated application of a TS suffix does not change the semantics of a sequence, so we can apply it just once and disregard all other sequences.

<span id="page-14-4"></span>**Lemma 4.** Let 
$$X \in \{T, S\}^*$$
. Then  $XTS \equiv XTSTS$ .

An immediate consequence of this result is that, through elimination of consecutively repeated operators via idempotence and of consecutively repeated TS sub-sequences via Lemma [4,](#page-14-4) we can restrict our attention to a set of just eight sequences, because any sequence is equivalent to one of those.

<span id="page-14-5"></span>**Theorem 2.** Let 
$$X \in \{T, S\}^*$$
. Then  $\exists Y \in \{\varepsilon, T, S, TS, ST, TST, STS, STST\}$  such that  $X \equiv Y$ .

Figure [4](#page-15-0) shows a (transitively reduced) graph whose nodes correspond to the eight sequences mentioned in Theorem [2](#page-14-5) and whose arcs indicate containment. Thanks to the theorem, we have narrowed the space of possible sequences to analyze from an infinite set {T, S} ∗ to just these eight sequences.

### <span id="page-14-0"></span>4.3 Minimality and transitivity

Now that we have restricted our scope to a small set of representative sequences, we can discuss minimality and transitivity in detail, so as to eventually detect

<span id="page-15-0"></span>![](_page_15_Figure_0.jpeg)

Figure 4: A transitively reduced graph showing containment between sequences. Dashed border for incomplete sequences; grey background for non-transitive sequences; blue background for minimal-transitive sequences. All containment relationships are strict.

minimal-transitive sequences. Note that incomplete sequences can be immediately ruled out of our analysis: it is straightforward to show that S is not transitive, T is not minimal (it is indeed maximal) and ε is neither.

Minimality. Generally, any complete sequence not ending with S is nonminimal, in that it may contain conflicting preferences (possibly introduced by T) that turn out to be in contrast with other, more specific preferences. We exemplify this on ST. In the examples to follow, we shall refer to t-tuples with a single attribute on a single taxonomy about time.

<span id="page-15-1"></span>Example 11. Let F consist of P<sup>1</sup> and the more specific P2:

$$P_1 = \operatorname{\mathsf{autumn}} \succeq \operatorname{\mathsf{sep}}, \quad P_2 = \operatorname{\mathsf{sep10}} \succeq \operatorname{\mathsf{oct10}}.$$

By specificity, in F S , P<sup>1</sup> is replaced by the statement P<sup>3</sup> consisting of two clauses (grouped by curly brackets):

$$P_3 = \left\{ egin{array}{ll} \operatorname{autumn} \succeq \operatorname{sep} \wedge \neg \operatorname{sep} 10 \\ \operatorname{autumn} \wedge \neg \operatorname{oct} 10 \succeq \operatorname{sep} \end{array} 
ight.$$

In F ST, the clauses in P<sup>3</sup> transitively combine into P<sup>1</sup> again, since, e.g., the value sep30 is below sep but not sep10 and below autumn but not oct10; therefore oct10 ⪰ST sep10 holds. However, in F STS , P<sup>1</sup> is again replaced by P3, so that oct10 ̸⪰STS sep10, which shows that ST is not minimal.

All the containments indicated in Figure [4](#page-15-0) are strict, as can be shown through constructions similar to that of Example [11,](#page-15-1) so no sequence ending with T is minimal in {T, S} ∗ .

<span id="page-16-0"></span>**Lemma 5.** Let  $X \in \{T, S\}^*$ . Then XT is not minimal in  $\{T, S\}^*$ .

**Transitivity.** Transitivity is certainly achieved for any sequence ending with T: any relation  $\succeq_{\mathsf{XT}}$  is transitive by construction, which entails transitivity of  $\succ_{\mathsf{XT}}$ . However, the following result shows that, in the general case, no sequence ending with S is transitive.

<span id="page-16-1"></span>**Lemma 6.** Let  $X \in \{T, S\}^*$ . Then XS is not transitive.

Minimal-transitive sequences. As a consequence of Lemmas 5 and 6, we can state a major result, showing that transitivity and minimality in {T, S}\* are mutually exclusive.

<span id="page-16-3"></span>**Theorem 3.** No sequence is both transitive and minimal in  $\{T,S\}^*$ .

Moreover, we observe that all complete sequences starting with S are incomparable (i.e., containment does not hold in any direction) with those starting with T, as stated below (also refer to Figure 4).

<span id="page-16-2"></span>**Theorem 4.** Let  $X \in \{TS, TST\}$  and  $Y \in \{ST, STS, STST\}$ . Then  $X \not\sqsubseteq Y$  and  $Y \not\sqsubseteq X$ .

This property is shown for TS and STS in the next example.

<span id="page-16-4"></span>**Example 12.** Let F consist of the following statements:

$$P_1 = \mathsf{summer} \succeq \mathsf{spring}, \quad P_2 = \mathsf{jul21} \succeq \mathsf{jun}, \quad P_3 = \mathsf{may} \succeq \mathsf{jul}.$$

Then  $F^{\mathsf{T}}$  includes  $P_1$ ,  $P_3$  and the following 4 statements:

$$\begin{array}{ll} P_4 = \mathsf{summer} \succeq \mathsf{jul} & (P_1 + P_3), \, P_5 = & \mathsf{may} \succeq \mathsf{spring} & (P_3 + P_1), \\ P_6 = & \mathsf{may} \succeq \mathsf{jun} & (P_3 + P_2), \, P_7 = \mathsf{summer} \succeq \mathsf{jun} & (P_1 + P_6), \end{array}$$

while  $P_2$  is removed, as it is redundant with respect to  $P_7$ . No statement in  $F^{\mathsf{T}}$  is more specific than  $P_4$ , so  $P_4$  is in  $F^{\mathsf{TS}}$  and, e.g., jul21  $\succeq_{\mathsf{TS}}$  jul10 holds. In  $F^{\mathsf{S}}$ , instead,  $P_1$  (less specific than  $P_3$ ) is replaced by

$$P_8 = \left\{ \begin{array}{c} \operatorname{summer} \succeq \operatorname{spring} \wedge \neg \operatorname{may} \\ \operatorname{summer} \wedge \neg \operatorname{jul} \succeq \operatorname{spring} \end{array} \right.$$

So, now, by combining  $P_8$  (instead of  $P_1$ ) and  $P_3$ , in  $F^{\sf ST}$  we do not obtain  $P_4$  and then jul21  $\not\succeq_{\sf STS}$  jul10. With this, TS  $\not\sqsubseteq$  STS.

For the other non-containment, consider that, in  $F^{\sf ST},$   $P_2$  combines with  $P_8$  into the following statement:

$$P_9 = \mathsf{jul21} \succeq \mathsf{spring},$$

so that  $jul21 \succeq_{ST}$  may holds. No statement in  $F^{ST}$  is more specific than  $P_9$ , so  $jul21 \succeq_{STS}$  may also holds. Instead,  $jul21 \not\succeq_{TS}$  may, since  $F^{TS}$  is as  $F^{T}$ , but with  $P_8$  instead of  $P_1$ . Therefore  $STS \not\sqsubseteq TS$ .

The notion of minimal-transitive sequence captures the fact that transitivity cannot be waived, since we are indeed looking for the minimal sequences among those that are both complete and transitive. Only three sequences are both complete and transitive: ST, TST and STST, the first of which contains the last one and is therefore not minimal. The remaining two sequences are transitive, incomparable by Theorem [4,](#page-16-2) and, therefore, minimal in the set of complete and transitive sequences, i.e., TST and STST are minimal-transitive sequences.

#### Theorem 5. The only minimal-transitive sequences are TST and STST.

As observed in Theorem [4,](#page-16-2) the sequence STST, which removes less specific conflicting preferences before computing the first transitive closure, does not in general entail a set of preferences included in those induced by TST. We shall further characterize the behavior of these two sequences in Section [5,](#page-17-0) from a theoretical point of view, and, experimentally, in Section [6.](#page-19-0)

We also observe that the result of Theorem [3](#page-16-3) is inherent and that no finer granularity in the interleaving of T and S (e.g., by making S resolve one conflict at a time instead of all together) would remove this limitation: as Example [11](#page-15-1) shows, the presence of one single preference (oct10 ⪰ sep10) is sufficient to make the relation transitive but not minimal, and its absence to make it minimal but not transitive. The atomicity of this conflict is enough to conclude that it is unavoidable and that no method whatsoever (not just those based on the T and S operators) could solve it.

# <span id="page-17-0"></span>5 Computing the Best Results

### 5.1 Worst-case difference between TST and STST

As shown in Theorem [4,](#page-16-2) the two minimal-transitive semantics are incomparable, thus there will be t-relations r and initial preference relations ⪰ for which the best results delivered by the two semantics will differ. A legitimate question is: How much can these results be different? In order to answer this question we consider the maximum value of the cardinality of the difference of the results delivered by the two minimal-transitive semantics over all t-relations with n t-tuples and over all input preference relations ⪰. To this end, let us define, for any two sequences X and Y:

$$DIFFBEST(X, Y, n) = \max_{\succeq, |r| = n} \{ |\beta_{\succ x}(r) - \beta_{\succ y}(r)| \}$$

as the worst-case difference in the results delivered by X with respect to those due to Y, for any given cardinality of the target t-relation r. We can prove the following:

<span id="page-17-1"></span>Theorem 6. We have both DiffBest(TST, STST, n) = Θ(n) and DiffBest(STST,TST, n) = Θ(n).

From a practical point of view, Theorem 6 shows that there is no all-seasons minimal-transitive semantics. Furthermore, there can be cases (used in the proof of the theorem) in which the number of best results from any of the two semantics is comparable to n, whereas the other semantics returns  $\mathcal{O}(1)$  t-tuples. In Section 6 we will experimentally investigate the actual difference of results delivered by the two minimal-transitive semantics.

#### 5.2 A heuristics for computing the best results

In order to compute the best results according to the formula  $F^{\mathsf{X}}$  we adopt the well-known BNL algorithmic pattern [3]. We remind that BNL-like algorithms have worst-case quadratic complexity, although in practice they behave almost linearly [36]. Remind also that, according to Equation (1), given a preference formula  $F^{\mathsf{X}}(x,y)$  defining weak preferences, the corresponding strict preferences are those induced by the formula  $F^{\mathsf{X}}_{\succ}(x,y) = F^{\mathsf{X}}(x,y) \land \neg F^{\mathsf{X}}(y,x)$ .

The t-tuples that do not match any side of any clause in the preference formula correspond to those objects that the formula does not talk about and that can, thus, be considered irrelevant. As recognized in the germane literature [35], such objects are of little interest and, in the following, we shall therefore compute  $\beta$  so as to only include relevant t-tuples (i.e., those that satisfy either side of at least one clause of  $F^{X}$ , thus of  $F^{X}_{\succ}$  as well).

The algorithm keeps the current best t-tuples in the Best set. When a new t-tuple t is read, and t is found to be relevant, t is compared to the tuples in Best. Given  $t' \in Best$ , if  $t' \succ_{\mathsf{X}} t$  then t is immediately discarded. Conversely, t is added to Best and all t-tuples  $t' \in Best$  such that  $t \succ_{\mathsf{X}} t'$  are removed from the Best set. Eventually, we have  $\beta_{\succ_{\mathsf{X}}}(r) = Best$ .

An improvement to this basic scheme is to pre-sort the t-relation so that the t-tuples matching the left side of a clause and corresponding to lower-level values in the taxonomies come first. The rationale is that lower-level values are likely associated with a smaller amount of t-tuples, so that a smaller Best partial result can be found before scanning large amounts of data. Furthermore, such t-tuples are likely to be preferred to many others, in particular when specificity is a concern. More in detail, we scan r and, for each relevant t-tuple t (irrelevant t-tuples are immediately discarded) we compute a height index, hi(t), as follows: For any clause  $C(x,y) = C^b(x) \wedge C^w(y)$  such that  $C^b(t)$  holds, we consider the "height" of each value v occurring in the clause, computed as the distance of v from the leaves of its taxonomy. Then, the minimum height over predicates in  $C^b(t)$  and over all other matching clauses is used as value of hi(t), and t-tuples are sorted by increasing height index values; conventionally, when t matches no clauses, we set  $hi(t) = \infty$ .

**Example 13.** Consider a formula  $F = P_1 \vee P_2$ , where  $P_1$  and  $P_2$  are taken from Example 6. Then, we have  $F^{\mathsf{STST}} = P_3 \vee P_2 \vee P_4$ , where  $P_3 = \mathsf{white} \succeq \mathsf{red} \wedge \neg \mathsf{Amarone}$  and  $P_4 = \mathsf{Amarone} \succeq \mathsf{red} \wedge \neg \mathsf{Amarone}$ . Out of the t-tuples in

<span id="page-18-0"></span><sup>&</sup>lt;sup>2</sup>In case of non-functional taxonomies, in which a node may have more than one parent, we take the minimum distance.

Figure [1,](#page-1-0) d is irrelevant, while e does not match any clause, and thus hi(e) = ∞. Wines a and f match white in P3, which has height 1 (see Figure [2b\)](#page-5-1), so hi(a) = hi(f) = 1, while b and c match Amarone in both P<sup>2</sup> and P4, with hi(b) = hi(c) = 0. Thus, b and c come before a and f in the ordering, and e is last.

## <span id="page-19-0"></span>6 Experiments

In this section, we consider from a practical point of view the sequences of operators T, TST, and STST, discussed in the previous sections. The main goals of the experimental study are: (i) to understand the impact of the rewriting process on the overall query execution time and how this depends on the specific sequence at hand; (ii) to assess the effect of minimal-transitive sequences on (the cardinality of) the results of the β (Best) operator; (iii) to compare overall execution times incurred by minimal-transitive sequences with respect to baseline strategies in which either no rewriting occurs or only the transitive closure of the input formula is computed; (iv) to measure the effects of the heuristics presented in Section [5.](#page-17-0) In particular, we study how efficiency and effectiveness are affected by taxonomy's size and morphology, dataset size, number of attributes, and number and type of preferences. The relevant parameters used in our analysis are summarized in Table [1.](#page-19-1)

In summary, we show that: the rewriting due to the minimal-transitive sequences TST and STST incurs a low overhead across all tested scenarios; such sequences are effective both in reducing the cardinality of β and in achieving substantial speedup with respect to baseline strategies, and that the speedup is further incremented when adopting our heuristics.

<span id="page-19-1"></span>Table 1: Operating parameters for performance evaluation (defaults, when available, are in bold).

| Full name                 | Tested value                |
|---------------------------|-----------------------------|
| Taxonomy's depth δ        | 2, 3, 4, 5, 6, 7, 8, 9, 10  |
| Taxonomy's fanout f       | 2, 3, 4, 5, 6, 7, 8, 9, 10  |
| Synthetic taxonomy's kind | regular, random, scale-free |
| # of attributes d         | 1, 2, 3, 4, 5               |
| # of input clauses c      | 2, 4, 6, 8, 10              |
| # of maximal values       | 2, 4, 6, 8, 10              |
| Type of preferences       | conflicting, contextual     |
| Dataset size N            | 10K, 50K, 100K, 500K, 1M    |

### 6.1 Taxonomies, datasets, and preferences

We use two families of taxonomies: synthetic and real taxonomies.

We run our tests on three kinds of synthetic taxonomies: regular, random and scale-free. A regular taxonomy is generated as a forest of f ("fanout") rooted trees consisting of  $\delta$  levels and f children for each internal node. The total number of nodes is therefore  $\sum_{i=1}^{\delta} f^i$ , i.e.,  $\frac{f(f^{\delta}-1)}{f-1}$ . A random taxonomy is generated as in the previous case, but the fanout of each node is Poisson distributed with an average of f. The default values for f and  $\delta$  are chosen to match the size of the real taxonomies used in the experiments (15-20K nodes). Finally, a scale-free taxonomy targets the same number of nodes, but following a power-law distribution (which is observed to be a recurrent structure, e.g., in the Semantic Web; see [70, 71]), for the fanout. Scale-free taxonomies generated this way (with reasonable exponents around 2.7) are typically very deep (between 30 and 60 levels). All synthetic taxonomies are functional by construction, i.e., every node has exactly one parent. Synthetic datasets of various sizes are generated by drawing values uniformly at random from a different taxonomy for each attribute.

We adopt two real taxonomies and datasets: flipkart<sup>3</sup> and UsedCars<sup>4</sup>. The former lists product categories of various kinds and consists of 15,236 nodes (of which 12,483 leaf categories) and 15,465 arcs spread throughout 10 levels. This taxonomy is non-functional, in that there exist nodes with more than one parent, i.e., some products belong to more than one category. Product info is available as a t-relation consisting of 19,673 t-tuples that also include original price, discounted price, and user rating, rendered here as attributes associated with a "flat" taxonomy with three values (e.g., "high", "medium", "low"). UsedCars features a large collection of used vehicles for sale consisting, after cleaning, of 232,470 t-tuples including, among others, price range (as a flat taxonomy) and model. Models are organized in a functional taxonomy, with 14,588 nodes and 14,540 leaves, over three levels (besides model name and make, we obtained country information via the Car Models List DB<sup>5</sup>).

The study of the best taxonomy representation in the general case is orthogonal with respect to the problems we study in this paper (see, e.g., [45]). However, given the taxonomies we deal with, it is convenient to precompute all paths in order to speed up all taxonomy-based computations, e.g., establishing when a value is more specific than another.

For our experiments, we consider two common types of preferences, discussed below: conflicting preferences and contextual preferences. We omit the results concerning other common types of preferences, as their behavior is not essentially different.

A pair of *conflicting preference* statements has the following form:

$$P_1 = v_1 \succeq v_2, \quad P_2 = v_2' \succeq v_1,$$

where  $v_1$  and  $v_2$  are maximal values (i.e., tree roots) of the same taxonomy  $T_i$  and  $v_2' \leq_{V_i} v_2$ . Clearly,  $P_2$  is more specific than  $P_1$ .

The second kind of preferences, used for experiments on multi-attribute relations, are pairs of conflicting *contextual preferences*, i.e., conflicting preferences

<span id="page-20-0"></span><sup>3</sup>https://www.flipkart.com

<span id="page-20-1"></span><sup>4</sup>https://www.kaggle.com/austinreese/craigslist-carstrucks-data

<span id="page-20-2"></span> $<sup>^5 {\</sup>tt https://www.teoalida.com/cardatabase/car-models-list}$ 

applied to one attribute, in which the other attributes are used to establish a sort of "context" of applicability. A pair of contextual preferences is of the following form:

$$P_{1} = v_{1}^{(1)} \wedge v^{(2)} \wedge \ldots \wedge v^{(d)} \succeq v_{2}^{(1)} \wedge v^{(2)} \wedge \ldots \wedge v^{(d)}, P_{2} = v_{2}^{(1)} \wedge v^{(2)} \wedge \ldots \wedge v^{(d)} \succeq v_{1}^{(1)} \wedge v^{(2)} \wedge \ldots \wedge v^{(d)},$$

where the (i) superscript denotes values from taxonomy  $T_i$ ,  $v_1^{(1)}$  and  $v_2^{(1)}$  are maximal in  $T_1$ , and  $v_2'^{(1)} \leq_{V_i} v_2^{(1)}$ . Note that, when there are d=1 attributes, this is just a pair of conflicting preferences. For real data, flat taxonomies are used for context attributes. An example of contextual preference is given by statement  $P_4$  in Example 6.

### 6.2 Results: computation of the output formula

In order to assess feasibility of the computation of the preference formula resulting after applying a sequence of operators, we report the corresponding execution time averaged out over 100 different runs (as measured on a machine sporting a 2,3 GHz 8-Core Intel Core i9 with 32 GB of RAM).

Our first experiments test the impact of the characteristics of the taxonomy in the case of synthetic taxonomies and one pair of conflicting preferences. For regular taxonomies, computing  $F^{\mathsf{T}}$  (0.5ms on average) is generally faster than computing  $F^{\mathsf{STST}}$  (1.5ms) and  $F^{\mathsf{TST}}$  (2.7ms) and neither f nor  $\delta$  affect the computation time significantly. Similar times are obtained with random taxonomies. With scale-free taxonomies the same relative costs are kept, but times are slightly higher, due to the much deeper structure, and tend to decrease as the number of maximal nodes increases, as shown in Figure 5a; still, all times are well under 0.2s and thus negligible with respect to the time required for computation of  $\beta$ , as will be shown in Section 6.3.

Figure 5b shows that the time for computing the formula grows with the number of input clauses, with times always below 0.5s.

For a multi-attribute scenario, Figure 5c shows the behavior with contextual preferences as the number of attributes varies. The resulting formula is always computed in less than 0.01s; times slightly grow as the number of attributes grows, but remain low.

We now turn to the case of real taxonomies. With UsedCars, which is functional, results are very similar to those obtained with synthetic taxonomies and thus not shown here in the interest of space. We then test on flipkart, which is non-functional, the case of conflicting preferences as the number of input clauses c varies. This has an impact on the overhead for determining redundancies in formulas and for checking clause satisfiability when computing T. Indeed, both require checking whether two values  $v_1$  and  $v_2$  have a common descendant in the taxonomy, which is immediate in the case of functional taxonomies, as it suffices to check whether there is a path from  $v_1$  to  $v_2$  or vice versa. However, for non-functional taxonomies this check may require extracting all descendants of  $v_1$  and  $v_2$ , which may be expensive for large taxonomies, especially when  $v_1$ 

<span id="page-22-3"></span><span id="page-22-2"></span><span id="page-22-0"></span>![](_page_22_Figure_0.jpeg)

<span id="page-22-4"></span>Figure 5: Time for computing the formula: various settings.

<span id="page-22-7"></span><span id="page-22-5"></span>![](_page_22_Figure_2.jpeg)

<span id="page-22-6"></span>Figure 6: Computing β with default parameter values.

and v<sup>2</sup> are maximal values. Yet, for taxonomies in which only few nodes have more than one parent (like flipkart, with 170 such nodes), it is convenient to keep track of those nodes at taxonomy load time; with this, we can check the existence of a common descendant between v<sup>1</sup> and v<sup>2</sup> by checking whether there is a path to both from one of those nodes (if they are not the descendant of one another). As Figure [5d](#page-22-4) shows, the times measured with the flipkart taxonomy are only slightly higher than with synthetic taxonomies (and always sub-second).

### <span id="page-22-1"></span>6.3 Results: computation of β

As discussed in Section [5,](#page-17-0) we restrict the β operator to act only on relevant t-tuples. In the same vein, we shall only consider preferences inducing a nonempty set of relevant t-tuples.

With conflicting preferences and default parameter values on regular tax-

onomies, the amount of relevant t-tuples is roughly 40% of the size of a synthetic dataset. Figure [6a](#page-22-5) shows that both T and ε retain about half of the relevant t-tuples (which is both the average and the median value we obtained), while TST and STST retain less than 2% in the median case (the average value goes up to 20% due to runs with unfocused input formulas referring to values not in the dataset). This is reflected in the computation times, shown in Figure [6b,](#page-22-6) which are consistently around 24s for T and 10s for ε, but nearly two orders of magnitude smaller in the median case for TST and STST. With both scale-free and random taxonomies, the amount of relevant t-tuples varies much more (with an average still around 40%), but times are on average one order of magnitude smaller for TST and STST than for T, with results for the latter covering almost the entire dataset due to the lack of conflict resolution.

We observe that the application of T alone corresponds to the work performed by preference evaluation methods that only aim at guaranteeing transitivity, e.g., [\[48,](#page-34-3) [12,](#page-30-0) [37\]](#page-33-3), which are therefore outperformed by our approach. The inability of T to deal with conflicting preferences, thus generating many indifferent t-tuples, which in turn induce (very) large result sets, indeed applies to all our scenarios. Similar observations apply to ε (i.e., the empty sequence, corresponding to the input formula), which represents the action of works on preference evaluation using no rewriting whatsoever, such as [\[11,](#page-30-1) [53\]](#page-34-1). Additionally, the results obtained via ε would be totally unreliable, due to lack of transitivity (see Example [7\)](#page-8-1). We thus refrain from considering T and ε from now on.

We now analyze the cost incurred by the computation of β as we deviate from standard parameter values. In the case of contextual preferences, adding context makes the β set leaner and, thus, easier to compute, so that times are under 1s already with two attributes. As usual, STST is slightly quicker to compute, since it gives rise to a smaller formula (although its strict version coincides with that of TST, and thus their cardinalities coincide).

As already visible in Figure [6,](#page-22-7) random preference formulas may fail to represent a meaningful specification of preferences, thus leading to very large result sets. For this reason, we disregard such formulas and, in particular, in the next experiments we only retain those "good runs" in which either TST or STST produce less than 2% of the t-tuples in the dataset. Figure [7a](#page-24-0) shows how the cardinality of β varies, under these hypotheses and default parameter values, as the number of input clauses c varies, thus confirming that STST typically leads to a smaller result than TST.

We now consider the heuristics described in Section [5,](#page-17-0) which sorts the trelation according to increasing height index values. Figure [7b](#page-24-1) compares times obtained with the heuristic sort strategy (marked with an H subscript) to those obtained with no heuristics as the number of input clauses c varies. The sort takes between 3% and 10% of the total time spent for computing β, yet the use of the proposed heuristics largely outperforms standard executions, with times never exceeding 2s; without the heuristics, times diverge to well over 100s, on average, in the more expensive scenarios.

Having ascertained the suitability of the heuristic sort, we demonstrate its

<span id="page-24-0"></span>![](_page_24_Figure_0.jpeg)

<span id="page-24-1"></span>Figure 7: Synthetic datasets: conflicting preferences, varying the number of input clauses c (only good runs).

<span id="page-24-2"></span>![](_page_24_Figure_2.jpeg)

<span id="page-24-3"></span>Figure 8: Synthetic datasets: varying the dataset size N (only good runs, size in logarithmic scale).

<span id="page-25-0"></span>![](_page_25_Figure_0.jpeg)

<span id="page-25-1"></span>Figure 9: flipkart: conflicting preferences, varying the number of input clauses c (only good runs).

<span id="page-25-2"></span>![](_page_25_Figure_2.jpeg)

Figure 10: flipkart: contextual preferences, varying the number of attributes d (only good runs).

scalability with the experiment shown in Figure [8,](#page-24-2) which shows a linear trend for times as the size N of the dataset varies, while cardinalities tend to grow logarithmically.

The trends shown with synthetic data are confirmed with real data on flipkart. Figure [9a](#page-25-0) shows that the cardinality of β typically grows as the number of input clauses grows. Consequently, Figure [9b](#page-25-1) shows times slightly growing with the number of input clauses, but always under 2.1s. The case of contextual preferences is shown in Figure [10,](#page-25-2) where times decrease as the number of attributes grows, since the number of relevant t-tuples decreases with the number of applied contexts. For the same reason, the cardinality of β is higher with 2 or 3 attributes than with 4; however, with only 1 attribute (and thus no context) the cardinality is the lowest, since the t-tuples satisfying the most specific preference are not filtered out by contexts.

For experiments on UsedCars, we collected preferences from a set of 107 users by means of a Web interface allowing the specification of statements in the simplified notation presented in Section [2](#page-4-0) through an expandable tree-view of the taxonomy (see Figure [11a\)](#page-26-1). After instructing users on how to specify preferences (even conflicting ones), we observed an average of 3.4 statements (from 2 to 9) per query and as many as 78% of cases of conflicts. Figure [11b](#page-26-2) shows

![](_page_26_Figure_0.jpeg)

<span id="page-26-3"></span><span id="page-26-2"></span><span id="page-26-1"></span>Figure 11: User interface and experiments on UsedCars.

box plots representing the distributions of cardinalities of β obtained with userdefined preferences, which confirms that STST tends to produce slightly smaller results than TST. We observe that such cardinalities, typically corresponding to the number of cars available for a specific model and price range, are very low with respect to the dataset size (and could be further reduced if filters based on other criteria, such as mileage, were applied). Execution times (Figure [11c\)](#page-26-3) are, on average, below 10s for both sequences, and thus overall acceptable and comparable with the measurements obtained with similarly sized synthetic data (Figure [8b\)](#page-24-3).

# <span id="page-26-0"></span>7 Related Works and Discussion

In spite of the many works on the use of qualitative preferences for querying databases (see, e.g., [\[69\]](#page-36-0)), only a few address the issues arising when attributes' domains exhibit a hierarchical structure.

Preferences in OLAP systems are considered in [\[37\]](#page-33-3), where an algebraic language, based on that in [\[48\]](#page-34-3), is adopted. Preferences on attributes are only of an absolute type, stating which are the most (resp. least) preferred values at a given "level" of a dimensional attribute. Preferences are then propagated along levels, with no concern for the combination of preferences, less so conflicting ones.

Lukasiewicz et al. [\[53\]](#page-34-1) extend the Datalog+/- ontological language with qualitative preferences, yet they do not address the problems arising from conflicting preferences. In a subsequent work [\[52\]](#page-34-4), the authors assume that, besides the order generated by the preferences, another linear order exists, originating from probabilistic scores attached to specific objects. Since the two orders may conflict, ad-hoc operators for compromising among the two orders are introduced and evaluated. Although [\[52\]](#page-34-4) considers conflicts, these are not among preferences and their solutions are not applicable to the scenario we consider in this paper.

To the best of our knowledge, no other work addresses the exact same issues we tackle here. Yet, Section [6.3](#page-22-1) has shown how existing methods (those that just enforce transitivity as well as works on preference evaluation using no rewritings) would be unsuitable to meet the goals we set in this paper.

The specificity principle on which we have based the definition of our S operator follows a long-standing tradition in the AI and KR fields, in which conflicts arising from contradictory evidences (antecedents) are solved by means of non-monotonic reasoning. However, in this context, the issue of inheritance of properties, which can be dealt with in different ways according to the adopted reasoning theory (see, e.g., [\[43\]](#page-33-0)), leads to problems that are quite different from those we have considered in this paper.

The need to address conflicts arising from preferences was also observed in [\[23\]](#page-31-2). The framework proposed there allows for a restricted form of taxonomies (with all values organized into distinct, named levels) and hints at an ad hoc procedure with very limited support for conflict resolution; the focus of [\[23\]](#page-31-2) is, however, on the downward propagation of preferences.

A kind of specificity principle was also considered in [\[24\]](#page-31-0), albeit on a different preference model (using strict rather than weak preferences) and a different scenario, in which preferences are to be combined across different contexts [\[59\]](#page-35-1). In that work, given two conflicting preferences, e.g., a ≻ b, which is valid in a context c, and b ≻ a valid in context c ′ , if context c is more specific than c ′ then a ≻ b wins and b ≻ a is discarded. Thus, specificity considered in [\[24\]](#page-31-0) concerns contexts, whereas, in the present paper, specificity has to do with preference statements that involve values at different levels of detail in the taxonomies. Conflicts in [\[24\]](#page-31-0) are at the level of a single pair of objects (since no language for specifying preferences was considered there), whereas in the present work we deal with conflicts between preference statements, which in general involve many pairs of objects - a fact that requires a solution incomparable with those adopted in [\[24\]](#page-31-0).

A line of research that is only apparently related to ours concerns the problem of propagating preferences across the nodes/terms of an ontology, see, e.g., [\[9,](#page-30-2) [10,](#page-30-3) [61\]](#page-35-2). Given "interest scores" attached to some terms, these works focus on (numerical) methods to combine and propagate such scores to "similar" terms in the ontology.

A definitely relevant issue, orthogonal to our focus and thus outside the scope of this paper, is that of preference elicitation. This problem has been thoroughly studied in various fields, such as Recommender Systems, decision making, marketing, and behavioral economics, with remarkable recent attention on relative preferences, either expressed with pairwise comparisons or inferred from absolute preferences [\[47,](#page-34-5) [46\]](#page-34-6).

Common methods to solve conflicts among preferences are based on the use of operators, the most well-known being Pareto and Prioritized composition [\[12,](#page-30-0) [48,](#page-34-3) [24\]](#page-31-0). Given a conflict between a and b originating from two different preference statements, Pareto composition just drops both preferences a ≻ b and b ≻ a. Conversely, Prioritized composition a priori assumes that one of the two statements is more important than the other, and then solves the conflict by retaining the corresponding preference. We have no such a-priori notion of priority, which might be hard to define in practice; rather, we rely on a definition of specificity that dynamically determines if a statement takes precedence over another depending on the available taxonomies.

Many algorithms have been devised to answer preference queries, although most of them work only for numerical attributes [\[49\]](#page-34-7). Among the algorithms that can be applied to arbitrary strict partial orders ≻, BNL [\[3\]](#page-29-1) is undoubtedly the most well-known among those that compute the result sets by means of dominance tests. Improvements to the BNL logic, such as those found in the SFS [\[13\]](#page-30-4) and SaLSa [\[1\]](#page-29-2) algorithms, require the input relation to be topologically sorted, which in these algorithms is based on the presence of numerical attributes. A different approach, pioneered in [\[35\]](#page-33-2), avoids (most of the) dominance tests by partitioning the domain of (relevant) tuples into a set of equivalence classes, where each class includes all and only those tuples whose values are the best for a subset of the input preference statements. For instance, a statement like (A<sup>i</sup> = v) ⪰ (A<sup>i</sup> = v ′ ) induces two equivalence classes, the first including all tuples with value v for attribute A<sup>i</sup> , and the second those with value v ′ . For each equivalence class a different SQL query is then executed, until it is guaranteed that no further optimal tuples exist. However, since the number of equivalence classes is exponential in the number of input statements, this approach cannot be adopted in our framework, in which the rewritten formula to be evaluated, due to the transitive closure operator, can well contain tens of statements.

Common practice typically focuses on the specification of quantitative preferences, for instance by means of a function expressing a score based on the attribute values, as is commonly done in top-k queries [\[44,](#page-33-4) [57,](#page-35-3) [58\]](#page-35-4). Recent works have tried to combine the qualitative nature of (Pareto) dominance with the quantitative aspects of ranking [\[21,](#page-31-3) [17,](#page-31-4) [19,](#page-31-5) [18,](#page-31-6) [2,](#page-29-3) [20,](#page-31-7) [67,](#page-36-4) [22\]](#page-31-8).

The specification of preferences is sometimes expressed through constraints of a "soft" nature, i.e., which can be violated. It should be interesting to combine the effects of the specification of "hard" constraints, such as the integrity constraints of a database, commonly adopted for query optimization and integrity maintenance [\[55,](#page-35-5) [15,](#page-30-5) [16,](#page-31-9) [54,](#page-35-6) [56,](#page-35-7) [14,](#page-30-6) [29,](#page-32-0) [28,](#page-32-1) [27,](#page-32-2) [8\]](#page-30-7), or even of structural constraints governing access to data [\[7,](#page-30-8) [8,](#page-30-7) [6,](#page-29-4) [5\]](#page-29-5), with the techniques studied in this paper for retrieving the best options. A more tolerant approach consists in coping with the presence of inconsistent or missing values [\[28,](#page-32-1) [27,](#page-32-2) [29,](#page-32-0) [30\]](#page-32-3); in such cases, it would be interesting to understand how the amount of such an inconsistency in the data [\[38,](#page-33-5) [31,](#page-32-4) [39,](#page-33-6) [40,](#page-33-7) [41,](#page-33-8) [42\]](#page-33-9) may affect the results.

We also observe that preference elicitation and management are typical parts of data preparation pipelines, which might then involve data subsequently processed by Machine Learning algorithms [\[62,](#page-35-8) [64,](#page-36-5) [65,](#page-36-6) [66\]](#page-36-7) and retrieved from heterogeneous sources, including RFID [\[33,](#page-32-5) [32\]](#page-32-6), pattern mining [\[63\]](#page-35-9), crowdsourcing applications [\[34,](#page-32-7) [4,](#page-29-6) [51\]](#page-34-8), and streaming data [\[26\]](#page-32-8).

# <span id="page-29-0"></span>8 Conclusions

In this paper we have tackled the problem of finding the best elements from a repository on the basis of preferences referring to values that are more generic than the underlying data and may involve conflicts. To this aim, we have introduced and formally investigated two operators for enforcing, in a given collection of preferences, the properties of specificity, which can solve conflicts, and transitivity, which guarantees the soundness of the final result. We have then characterized the limitations that can arise from their combination and identified the best ways in which they can be used together. We have finally proposed a technique based on an original heuristics for selecting the best results associated with given sequences of operators and shown, with a number of experiments over both synthetic and real-world datasets, the effectiveness and practical feasibility of the overall approach. Future work includes extending our framework to more general scenarios in which domain values are connected by ontological relationships, as is the case in Ontology-Based Data Access [\[72\]](#page-36-8).

#