Dupligänger
===========

*Dupligänger* is a reference-based, UMI-aware, 5'-trimming-aware PCR duplicate
removal pipeline.

Usage: dupliganger [options] <command> [<args>...]


*Dupligänger* is a pipeline.  Each stage of the pipeline is run by passing a
'command' to *Dupligänger*.  The commands / pipeline-steps (in order) are as
follows::

   remove-umi         1. Annotate read names with UMIs (clip inline UMIs if needed).
   remove-adapter     2. Remove adapters ('Cutadapt' wrapper).
   qtrim              3. Quality trim ('Trimmomatic' wrapper).
   annotate-qtrim     4. Annotates quality trimmed file(s).
   align              5. Align reads to a reference genome assembly (performed manually by user).
   dedup              6. Use the alignment to remove PCR duplicates.

While generally used only by the developers of *Dupligänger*, the 'dedup'
command is comprised of the following *Dupligänger* commands run in the
following order::

    build-read-db      1. Build a database of aligned reads.
    build-location-db  2. Build a database of locations of aligned reads.
    build-dup-db       3. Build a database of PCR duplicates.

Options::

    -o OUT_DIR      Place results in directory OUT_DIR.
    --compress      Compress output.

Note:
    *Dupligänger* supports (and autodetects) input FASTQ files that are gzipped.

See 'dupliganger help <command>' for more information on a specific command.

Documentation
=============

For further information on *Dupligänger*, please see the full documentation at
https://github.com/uoregon-postlethwait/dupliganger

Authors
=======

* Jason Sydes - Conceptual Design and Software Engineering
* Peter Batzel - Conceptual Design
* John H. Postlethwait - Project Advisor

Funding
=======

*Dupligänger* has been funded by the following grants:

* NIH R01 OD011116 - Resources for Teleost Gene Duplicates and Human Disease
* NIH R24 OD011199 - Advancing the Scientific Potential of Transcriptomics in Aquatic Models
* NIH R24 OD018555 - Development of Aquatic Model Resources for Therapeutic Screens
* NSF PLR-1543383 - Antarctic Fish and MicroRNA Control of Development and Physiology 
