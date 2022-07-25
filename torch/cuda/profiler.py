import tempfile
import contextlib
from . import cudart, check_error, init as cuda_init
from .. import _C
import subprocess

DEFAULT_FLAGS = [
    "gpustarttimestamp",
    "gpuendtimestamp",
    "gridsize3d",
    "threadblocksize",
    "streamid",
    "enableonstart 0",
    "conckerneltrace",
]


def init(output_file, flags=None, output_mode='key_value'):
    rt = cudart()
    if not hasattr(rt, 'cudaOutputMode'):
        raise AssertionError("HIP does not support profiler initialization!")
    flags = DEFAULT_FLAGS if flags is None else flags
    if output_mode == 'key_value':
        output_mode_enum = rt.cudaOutputMode.KeyValuePair
    elif output_mode == 'csv':
        output_mode_enum = rt.cudaOutputMode.CSV
    else:
        raise RuntimeError("supported CUDA profiler output modes are: key_value and csv")
    with tempfile.NamedTemporaryFile(delete=True) as f:
        f.write(b'\n'.join(f.encode('ascii') for f in flags))
        f.flush()
        check_error(rt.cudaProfilerInitialize(f.name, output_file, output_mode_enum))


def start():
    check_error(cudart().cudaProfilerStart())


def stop():
    check_error(cudart().cudaProfilerStop())


@contextlib.contextmanager
def profile():
    try:
        start()
        yield
    finally:
        stop()


def enable_memory_history():
    cuda_init()
    _C._cuda_enableMemoryHistory()

def _frame_fmt(f):
    c, i = f
    fname = c.co_filename.split('/')[-1]
    func = c.co_name
    return f'{fname}:{i}:{func}'

def save_memory_flamegraph(fname='memory.txt'):
    ss = _C._cuda_memorySnapshot()
    with open(fname, 'w') as f:
        for x in ss:
            for b in x['blocks']:
                if 'history' not in b:
                    continue
                for h in b['history']:
                    sz = h['real_size']
                    frames = h['frames']
                    stuff = ';'.join([ _frame_fmt(f) for f  in reversed(frames) ])
                    f.write(f'{b["state"]};{stuff} {sz}\n')
