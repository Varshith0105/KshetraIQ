"""Compatibility patch for deserializing Scikit-learn ColumnTransformer artifacts.

Ensures that models pickled under scikit-learn 1.6 can be unpickled in later versions
where `_RemainderColsList` was refactored.
"""

import sys
import sklearn.compose._column_transformer as ct


class _RemainderColsList(list):
    """Compatibility stub for unpickling legacy ColumnTransformer remainder lists."""
    pass


if not hasattr(ct, "_RemainderColsList"):
    setattr(ct, "_RemainderColsList", _RemainderColsList)
