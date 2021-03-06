import pandas as pd
from root_pandas import read_root
from root_numpy import list_branches
from root_numpy import array2root
from pandas.util.testing import assert_frame_equal
import numpy as np
import ROOT
import os
import warnings

def test_read_write():
    df = pd.DataFrame({'x': [1,2,3]})
    df.to_root('tmp.root')
    df_ = read_root('tmp.root')
    os.remove('tmp.root')

    df.to_root('tmp.root', key='mykey')
    df_ = read_root('tmp.root', key='mykey')
    assert_frame_equal(df, df_)
    os.remove('tmp.root')

    tf = ROOT.TFile('tmp.root', 'recreate')
    tt = ROOT.TTree("a", "a")

    x = np.array([1])
    x[0] = 42
    tt.Branch('x', x, 'x/D')

    tt.Fill()
    x[0] = 1
    tt.Fill()
    tt.Write()
    tf.Close()

    # Read when no index is present
    df = read_root('tmp.root', columns=['x'])
    os.remove('tmp.root')

def test_ignore_columns():
    df = pd.DataFrame({'x': [1,2,3], 'y1': [2,3,4], 'y2': [3,4,5]})
    df.to_root('tmp.root')

    df = read_root('tmp.root', ignore=['y1'])
    assert(df.columns[0] == 'x' and df.columns[1] == 'y2')

    df = read_root('tmp.root', ignore=['y*'])
    assert(df.columns == ['x'])

    # Test interaction with columns kwarg
    df = read_root('tmp.root', columns=['y*'], ignore=['*1'])
    assert(df.columns == ['y2'])

    os.remove('tmp.root')

def test_array_element_columns():
    tf = ROOT.TFile('tmp.root', 'RECREATE')
    tt = ROOT.TTree("a", "a")

    length = np.array([3])
    x = np.array([0, 1, 2], dtype='float64')
    tt.Branch('length', length, 'length/I')
    tt.Branch('x', x, 'x[length]/D')
    tt.Fill()
    x[0] = 0
    x[1] = 1
    x[2] = 2
    tt.Fill()
    tf.Write()
    tf.Close()

    branches = list_branches('tmp.root')

    df = read_root('tmp.root', columns="noexpand:x[0]")
    assert df.columns == ['x[0]']

    for i in df['x[0]']:
        assert i == 0

    os.remove('tmp.root')

def test_persistent_index():
    df = pd.DataFrame({'index': [42, 0, 1], 'x': [1,2,3]})
    df = df.set_index('index')
    df.index.name = 'MyAwesomeName'
    df.to_root('tmp.root')
    assert('__index__MyAwesomeName' in list_branches('tmp.root'))
    df_ = read_root('tmp.root')
    assert_frame_equal(df, df_)
    os.remove('tmp.root')

    # See what happens if the index has no name
    df = pd.DataFrame({'x': [1,2,3]})
    df.to_root('tmp.root')
    df_ = read_root('tmp.root')
    assert_frame_equal(df, df_)
    os.remove('tmp.root')

def test_chunked_reading():
    df = pd.DataFrame({'x': [1,2,3,4,5,6]})
    df.to_root('tmp.root')

    count = 0
    for df_ in read_root('tmp.root', chunksize=2):
        assert(not df_.empty)
        count += 1

    assert count == 3
    os.remove('tmp.root')

# Make sure that the default index counts up properly,
# even if the input is chunked
def test_chunked_reading_consistent_index():
    df = pd.DataFrame({'x': [1,2,3,4,5,6]})
    df.to_root('tmp.root', store_index=False)

    dfs = []
    for df_ in read_root('tmp.root', chunksize=2):
        dfs.append(df_)
        assert(not df_.empty)
    df_reconstructed = pd.concat(dfs)

    assert_frame_equal(df, df_reconstructed)

    os.remove('tmp.root')


def test_multiple_files():
    df = pd.DataFrame({'x': [1,2,3,4,5,6]})
    df.to_root('tmp1.root')
    df.to_root('tmp2.root')
    df.to_root('tmp3.root')

    df_ = read_root(['tmp1.root', 'tmp2.root', 'tmp3.root'])

    assert(len(df_) == 3 * len(df))

    # Also test chunked read of multiple files

    counter = 0
    for df_ in read_root(['tmp1.root', 'tmp2.root', 'tmp3.root'], chunksize=3):
        assert(len(df_) == 3)
        counter += 1
    assert(counter == 6)

    os.remove('tmp1.root')
    os.remove('tmp2.root')
    os.remove('tmp3.root')


def test_flatten():
    tf = ROOT.TFile('tmp.root', 'RECREATE')
    tt = ROOT.TTree("a", "a")

    length = np.array([3])
    x = np.array([0, 1, 2], dtype='float64')
    y = np.array([6, 7, 8], dtype='float64')
    tt.Branch('length', length, 'length/I')
    tt.Branch('x', x, 'x[length]/D')
    tt.Branch('y', y, 'y[length]/D')
    tt.Fill()
    x[0] = 3
    x[1] = 4
    x[2] = 5
    y[0] = 9
    y[1] = 10
    y[2] = 11
    tt.Fill()
    
    tf.Write()
    tf.Close()

    branches = list_branches('tmp.root')


    # flatten one out of two array branches
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df_ = read_root('tmp.root', flatten=['x'])
    assert('__array_index' in df_.columns)
    assert(len(df_) == 6)
    assert('length' in df_.columns.values)
    assert('x' in df_.columns.values)
    assert('y' not in df_.columns.values)
    assert(np.all(df_['__array_index'] == np.array([0, 1, 2, 0, 1, 2])))
    assert(np.all(df_['x'] == np.array([0, 1, 2, 3, 4, 5])))


    # flatten both array branches
    df_ = read_root('tmp.root', flatten=['x','y'])
    assert('__array_index' in df_.columns)
    assert(len(df_) == 6)
    assert(np.all(df_['__array_index'] == np.array([0, 1, 2, 0, 1, 2])))
    assert('length' in df_.columns.values)
    assert('x' in df_.columns.values)
    assert('y' in df_.columns.values)
    assert(np.all(df_['x'] == np.array([0, 1, 2, 3, 4, 5])))
    assert(np.all(df_['y'] == np.array([6, 7, 8, 9, 10, 11])))


    # Also flatten chunked data
    for df_ in read_root('tmp.root', flatten=['x'], chunksize=1):
        assert(len(df_) == 3)
        assert(np.all(df_['__array_index'] == np.array([0, 1, 2])))

    # Also test deprecated behaviour
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df_ = read_root('tmp.root', flatten=True)
    assert('__array_index' in df_.columns)
    assert(len(df_) == 6)
    assert(np.all(df_['__array_index'] == np.array([0, 1, 2, 0, 1, 2])))


    os.remove('tmp.root')




def test_drop_nonscalar_columns():
    array = np.array([1, 2, 3])
    matrix = np.array([[1, 2, 3], [4, 5, 6]])
    bool_matrix = np.array([[True, False, True], [True, True, True]])

    dt = np.dtype([
        ('a', 'i4'),
        ('b', 'int64', array.shape),
        ('c', 'int64', matrix.shape),
        ('d', 'bool_'),
        ('e', 'bool_', matrix.shape)
        ])
    arr = np.array([
        (3, array, matrix, True, bool_matrix),
        (2, array, matrix, False, bool_matrix)],
        dtype=dt)

    path = 'tmp.root'
    array2root(arr, path, 'ntuple', mode='recreate')
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = read_root(path, flatten=False)
        # the above line throws an error if flatten=True because nonscalar columns
        # are dropped only after the flattening is applied. However, the flattening
        # algorithm can not deal with arrays of more than one dimension.
    assert(len(df.columns) == 2)
    assert(np.all(df.index.values == np.array([0, 1])))
    assert(np.all(df.a.values == np.array([3, 2])))
    assert(np.all(df.d.values == np.array([True, False])))

    os.remove(path)

def test_noexpand_prefix():
    xs = np.array([1, 2, 3])
    df = pd.DataFrame({'x': xs})
    df.to_root('tmp.root')

    # Not using the prefix should throw, as there's no matching branch name
    try:
        df = read_root('tmp.root', columns=['2*x'])
    except ValueError:
        pass
    else:
        assert False

    # Could also use TMath::Sqrt here
    df = read_root('tmp.root', columns=['noexpand:2*sqrt(x)'])
    # Note that the column name shouldn't have the noexpand prefix
    assert np.all(df['2*sqrt(x)'].values == 2*np.sqrt(xs))

    os.remove('tmp.root')
