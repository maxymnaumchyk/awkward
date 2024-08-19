# BSD 3-Clause License; see https://github.com/scikit-hep/awkward/blob/main/LICENSE

from __future__ import annotations

import awkward as ak
from awkward._dispatch import high_level_function

__all__ = ("to_raggedtensor",)


@high_level_function()
def to_raggedtensor(ak_arr):
    """
    Args:
        ak_arr: Array-like data. May be a high level #ak.Array,
        or low-level #ak.contents.ListOffsetArray, #ak.contents.ListArray,
        #ak.contents.RegularArray, #ak.contents.NumpyArray

    Converts `ak_arr` (only ListOffsetArray, ListArray, RegularArray and NumpyArray data types supported)
    into a ragged tensor, if possible.

    If `ak_arr` contains any other data types (RecordArray for example) the function raises an error.
    """

    # Dispatch
    yield (ak_arr,)

    # Implementation
    return _impl(ak_arr)


def _impl(ak_arr):
    try:
        import tensorflow as tf
    except ImportError as err:
        raise ImportError(
            """install the 'tensorflow' package with:

        pip install tensorflow"""
        ) from err

    # unwrap the awkward array if it was made with ak.Array function
    # also transforms a python list to awkward array
    ak_arr = ak.to_layout(ak_arr, allow_record=False)

    if isinstance(ak_arr, ak.contents.numpyarray.NumpyArray):
        return tf.RaggedTensor.from_row_splits(
            values=ak_arr.data, row_splits=[0, ak_arr.__len__()]
        )
    else:
        flat_values, nested_row_splits = _recursive_call(ak_arr, ())

        return tf.RaggedTensor.from_nested_row_splits(flat_values, nested_row_splits)


def _recursive_call(layout, offsets_arr):
    try:
        # change all the possible layout types to ListOffsetArray
        if isinstance(layout, ak.contents.listarray.ListArray):
            layout = layout.to_ListOffsetArray64()
        elif isinstance(layout, ak.contents.regulararray.RegularArray):
            layout = layout.to_ListOffsetArray64()
        elif (not isinstance(layout, ak.contents.listoffsetarray.ListOffsetArray)) and (
            not isinstance(layout, ak.contents.numpyarray.NumpyArray)
        ):
            raise TypeError(
                "Only arrays containing variable-length lists (var *) or"
                " regular-length lists (# *) of numbers can be converted into a TensorFlow RaggedTensor"
            )

        # recursively gather all of the offsets of an array
        offsets_arr += (layout.offsets.data,)

    except AttributeError:
        # at the last iteration form a ragged tensor from the
        # accumulated offsets and flattened values of the array
        return layout.data, offsets_arr
    return _recursive_call(layout.content, offsets_arr)
