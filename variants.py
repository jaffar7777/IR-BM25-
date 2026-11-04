"""Shared source-page limits for collection, indexing, validation and search."""
VARIANT_PAGES = {'short': 5, 'medium7': 7, 'medium8': 8, 'medium9': 9, 'long': None}
VARIANTS = tuple(VARIANT_PAGES)
VARIANT_LABELS = {'short': 'Short', 'medium7': 'Medium (7 pages)', 'medium8': 'Medium (8 pages)',
                  'medium9': 'Medium (9 pages)', 'long': 'Long'}
