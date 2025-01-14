"""
Example usage:

python geo-datasets/boundaries/geoboundaries_ingest.py master 1_3_3 serial missing True

Where args are: branch, version, method, update mode, dry run

Note: when using parallel mode, be sure to spin up job first (manually or use job script)
      and use appropriate mpi command to run script

qsub -I -l nodes=5:c18c:ppn=16 -l walltime=48:00:00
mpirun --mca mpi_warn_on_fork 0 --map-by node -np 80 python-mpi /sciclone/aiddata10/geo/master/source/geo-datasets/boundaries/geoboundaries_ingest.py master 1_3_3 parallel missing True
mpirun --mca mpi_warn_on_fork 0 --map-by node -np 16 python geoboundaries_ingest.py master v4 parallel missing False

"""

import sys
import os
import time
import pandas as pd

# main_dir = os.path.join(
#     os.path.dirname(os.path.dirname(os.path.dirname(
#         os.path.abspath(__file__)))),
#     'geo-hpc')

# sys.path.insert(0, os.path.join(main_dir, 'utils'))
# sys.path.insert(0, os.path.join(main_dir, 'ingest'))

sys.path.insert(0, "/sciclone/aiddata10/geo/master/source/geo-hpc/utils")


import mpi_utility
from config_utility import BranchConfig

# import add_geoboundaries as add_gb
from add_geoboundaries import run

branch = sys.argv[1]

config = BranchConfig(branch=branch)

# check mongodb connection
if config.connection_status != 0:
    raise Exception("connection status error: {0}".format(
        config.connection_error))


# -------------------------------------------------------------------------

branch = "master"
version = "v4"


version = sys.argv[2]

data_dir = os.path.join(config.data_root, 'data/boundaries/geoboundaries', version)


if not os.path.isdir(data_dir):
    msg = 'Could not find directory for GeoBoundaries version ({}): \n\t {}'.format(
        version, data_dir)
    raise Exception(msg)


method = sys.argv[3]

if len(sys.argv) >= 5:
    update = sys.argv[4]
else:
    update = False

if len(sys.argv) >= 6:
    dry_run = sys.argv[5]
else:
    dry_run = False


qlist_raw = [os.path.join(data_dir, i) for i in os.listdir(data_dir)
         if os.path.isdir(os.path.join(data_dir, i))]
qlist_raw.sort()

#ignore_list = ["JPN", "NOR", "PHL", "NZL"]
# qlist = [i for i in qlist_raw if not any([j in i for j in ignore_list])]

# accept_list = []
# qlist = [i for i in qlist_raw if any([j in i for j in accept_list])]

qlist = qlist_raw

job = mpi_utility.NewParallel(parallel=method)


if job.rank == 0:
    print('GeoBoundaries found: {}'.format(len(qlist)))



def tmp_master_init(self):
    # start job timer
    self.Ts = int(time.time())
    self.T_start = time.localtime()
    print('Start: ' + time.strftime('%Y-%m-%d  %H:%M:%S', self.T_start))
    self.results = []


def tmp_master_process(self, worker_data):
    self.results.append(worker_data)


def tmp_master_final(self):

    # stop job timer
    T_run = int(time.time() - self.Ts)
    T_end = time.localtime()
    print('\n\n')
    print('Start: ' + time.strftime('%Y-%m-%d  %H:%M:%S', self.T_start))
    print('End: '+ time.strftime('%Y-%m-%d  %H:%M:%S', T_end))
    print('Runtime: ' + str(T_run//60) +'m '+ str(int(T_run%60)) +'s')
    print('\n\n')
    self.df = pd.DataFrame(self.results, columns=["task", "status", "error", "path"])
    output_path = os.path.join(data_dir, "results_{}.csv".format(time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime())))
    self.df.to_csv(output_path, index=False)


def tmp_worker_job(self, task_index, task_data):

    path = task_data

    try:
        with mpi_utility.Capturing() as output:
            run(path=path, version=version, config=config,
                    update=update, dry_run=dry_run)
        print('\n'.join(output))
        return (task_index, "Success", 0, path)
    except Exception as e:
        print("Error with {0}".format(path))
        return (task_index, "Error", e, path)


# init / run job
job.set_task_list(qlist)

job.set_master_init(tmp_master_init)
job.set_master_process(tmp_master_process)
job.set_master_final(tmp_master_final)
job.set_worker_job(tmp_worker_job)

job.run()
