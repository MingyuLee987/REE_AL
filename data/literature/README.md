# Additional literature collection

The local CSV files and collected_data.xlsx preserve the latest collection: 4,050 metadata records, 880 full-text papers, 4,648 machine-extracted candidates from 456 papers, and 503 checked measurements. These stages overlap and must not be added together.

checked_measurements.csv contains 216 author rebar measurements, 275 author mortar measurements and 12 reviewed alloy examples. Composition is incomplete in many records; these were not added to training.csv. hku_transformed_535_not_merged.csv is preserved separately because transformation and overlap require review.

The old evidence_path fields are relative to the original workspace layout. Resolve those paths under the archive directory below. It preserves outputs/expanded_collection/fulltext and outputs/expanded_collection/tables, plus the original collection scripts under best_model.

Archive: C:\Users\user\OneDrive - postech.ac.kr\바탕 화면\REE_AL_archive\20261022_cleanup

See docs/cleanup_manifest.json and data/provenance for the reorganization record and source composition history. CSV files remain local and ignored by Git.
