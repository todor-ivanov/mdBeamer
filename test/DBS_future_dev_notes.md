# DBS/DAS possible future developments
## Hybrid workflow management systems: CMS+DIRAC(X) or CMS+PAnda

- Author: Todor Ivanov
- Affiliation: University of Notre Dame
- Date: 18-03-2026

---

# Main assumptions[fontsize=\tiny]


### Main assumptions:


- The CMS Data `model` does not change [^1]
- We implement the new system and do not change patterns on how we use the DATA Book keeping system:
  * DBS - data discovery and resolution
  * Rucio - data movement

[^1]: https://github.com/todor-ivanov/CMSDiracAux


![CMS Data Model left:40%](png/cms-data-model_diagram_01.png){width=1.0 height=0.95\textheight}


---


# Main assumptions

### Main assumptions:



::: columns

::: column width=60% valign=top

::: fontsize=\tiny

```python[fontsize=\huge]
    if x:
        print("we are here")

```
:::

::: fontsize=\small

- The CMS Data `model` does not change [^1]
- We implement the new system and do not change patterns on how we use the DATA Book keeping system:
  * DBS - data discovery and resolution
  * Rucio - data movement





:::

:::
::: column width=40% valign=top

![CMS Data Model](png/cms-data-model_diagram_01.png){width=0.95 height=0.75\textheight}

:::
:::

[^1]: https://github.com/todor-ivanov/CMSDiracAux

---

# Test column

## Test Column

::: fontsize=\small

- The CMS Data `model` does not change[^2]
- We implement the new system and do not change patterns on how we use the DATA Book keeping system:
  * DBS - data discovery and resolution
  * Rucio - data movement


| A  | B  |
|----|----|
| 42 | 17 |
| 89 | 63 |
| 25 | 74 |



[^2]: https://github.com/todor-ivanov/CMSDiracAux



---

# First scenario

* Possible Places of interaction with DBS/DAS and eventual code changes (under diff conditions)
  * Read
  * CMS+DIRAC:[^1]
        * READ interactions:
          * in case the interaction between the systems (the CMS data resolution) happens through the DIRAC native DAtaPlacement system  (calls to Dirac Request manager + (or) Dirac File Catalog queries) - The code change should go inside the DIRAC system (not a good idea), but we do not know how extendable is this part of the DIRAC system (could it use a plugin based mechanism for adding extensions to the system similarly to the DIrac Transformations system) - The new component becomes native to the DIRAC system - the system does not evolve any more(may be impossible). Second obstacle - this approach means it would/should communicate with DBS/DAS  through its  protocol stack which is not HTTP API oriented (RPC calls etc.). - implies huge change on the DAS/DBS side
                * in case the interaction between the systems ( ....... ) happens at the transition layer, we hold the full controll, might require minimal to no DAS change in order to adopt new set of queries, may end up tied to scalability issues attributable only to the Internal Representation layer of CMSDiracAux. We also need to take into account about the early data resolution hich already happens in the early tages of the CMS workflows lifetime inside the WMCore central services, which are suposed to be preserved in the future acrhitecture - considering how could much more data could we query aggregate at an early stage....in the new workfllow model
        * WRITE interactions:
        * At job batch completion - the interaction should be initiated from which ever BookKeepoing system is serving the purpose  - for both DIRAC and DIRACx
        * alternative place of the change - at the translation layer interlinking the two systems - which means creating a parallel path for backpropagation completenss information and extra complication at the interlinking layer - CMSDiracAUX

        ( we are again talking about rebirth of WMBS)

    * CMS+DIRACX:
        * READ interactions: same logic as for CMS+DIRAC
    * CMS + Panda - give suggestions ..... no info so far


---

# Second scenario

### Main assumption:

We evlove DAS to a full fledged data aggregation and access service

- The CMS Data model does not change
- We implement the new system and do not change patterns on how we use the DATA Book keeping system:
  * DBS - data discovery and resolution
  * Rucio - data movement


## Second scenario

* DAS is already quering DBS and Rucio and is capable of providing full concept of data structure&placement and already delivers reliable data discovery and resolution infrastructure in such approach
    * we will heavily rely on DAS for this service, on all levels of workload granulrity - which means we  may start hitting it hard, so we may have to face scalability issues, but should not be unsolvable, since DAS is a thin layer infornt of DBS
    * we will still use DBS for metadata records as before, which means the only direct queries to DBS would be write on block requests
    * Rucio still serves th erole of DATA movement as is now. Nothing changes here

---

# Third scenario

## Move entire DBS content to Rucio use the Rucio's capabilities to handle metadata
* the same complexity introduction problem as the one which appears inside the Internal Representation layer for CMSDiracAux    
    * abstrations mismatch
    * GRanularity and Data storage levels mismatch - block/dataset misallignment yet again
    * Possible match is the data contents - physics objects  should not be too diffrerent , but the qurestion remains how capable is Rucio for hanling metadata at levels gowing down to luminosity sections and events
    * Possible scalability issues

* the good part - the whole project immedeately transforms into a single OPS action - pooring the metadata  contents inside Rucio

BUT the long term operation remains


---

# Conclusions


   MAIN MESSAGE: Provided the CMS data model does not change and the atomic unit still stays a luminosity section, no structural changes to the Data bookkeeping services are to be needed other than possible API interfaces evolution.
   It is not the job granularity and the way of we split the load over the data  which creates the pressure on DBS, It is the system level at which we initiate the interaction with DBS, because at different levels of the system we  we handle different levels of workload abstractions, which represent different workflow granularity and hence affect the frequency of  querying  and the amount of data transferred from the metadata system.

