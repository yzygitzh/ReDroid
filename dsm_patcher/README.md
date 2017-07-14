# README FOR DSM_PATCHER

* First, collect trace return value differences
    1. know method and event collection according to previous detection and comparison results
    2. start app as waiting for debug mode
    3. set trace targets as method collection
    4. fire events as event collection
    5. collect results

* Second, a comparison script
    1. comparing running differences
    2. generate formatted DSM (Dynamic State Modification)'s

* Third, do DSM
    1. get targets to modify return values according to comparison script result
    2. start app as waiting for debug mode
    3. set targets
