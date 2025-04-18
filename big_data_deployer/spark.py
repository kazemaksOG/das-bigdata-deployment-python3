#!/usr/bin/env python3

from __future__ import print_function
from .frameworkmanager import Framework, FrameworkVersion, FrameworkRegistry, get_framework_registry
from . import util
import glob
import os.path
import re

_SETTING_WORKER_INSTANCES = "worker_instances"
_SETTING_WORKER_CORES = "worker_cores"
_SETTING_WORKER_MEMORY = "worker_memory"
_ALL_SETTINGS = [
    (_SETTING_WORKER_INSTANCES, "worker instances to launch per node"),
    (_SETTING_WORKER_CORES, "cores available per worker instance to Spark"),
    (_SETTING_WORKER_MEMORY, "memory available per worker instance to spark")
]

class SparkFrameworkVersion(FrameworkVersion):
    def __init__(self, version, archive_url, archive_extension, archive_root_dir, template_dir):
        super(SparkFrameworkVersion, self).__init__(version, archive_url, archive_extension, archive_root_dir)
        self.__template_dir = template_dir

    @property
    def template_dir(self):
        return self.__template_dir

class SparkFramework(Framework):
    def __init__(self):
        super(SparkFramework, self).__init__("spark", "Spark")

    def deploy(self, spark_home, framework_version, machines, settings, log_fn=util.log):
        """Deploys Spark to a given set of workers and a master node."""
        if len(machines) < 2:
            raise util.InvalidSetupError(f"Spark requires at least two machines: a master and at least one worker, provided {machines}")

        # Extract settings
        try: 
            worker_instances = str(settings.pop(_SETTING_WORKER_INSTANCES))
            worker_cores = str(settings.pop(_SETTING_WORKER_CORES))
            worker_memory = str(settings.pop(_SETTING_WORKER_MEMORY))
        except KeyError as e:
            raise util.InvalidSetupError(f"Deploying error: setting missing {e.args[0]}")
        if len(settings) > 0:
            raise util.InvalidSetupError("Found unknown settings for Spark: '%s'" % "','".join(settings.keys()))

        # Select master and workers
        master = machines[0]
        workers = machines[1:]
        log_fn(0, "Deploying Spark driver on \"%s\", with %d workers." % (master, len(workers)))

        # Ensure that SPARK_HOME is an absolute path
        spark_home = os.path.realpath(spark_home)

        # Generate configuration files using the included templates
        template_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "conf", "spark", framework_version.template_dir)
        config_dir = os.path.join(spark_home, "conf")
        substitutions = {
            "__USER__": os.environ["USER"],
            "__MASTER__": master,
            "__WORKER_INSTANCES__": worker_instances,
            "__WORKER_CORES__": worker_cores,
            "__WORKER_MEMORY__": worker_memory
        }
        substitutions_pattern = re.compile("|".join([re.escape(k) for k in substitutions.keys()]))
        # Iterate over template files and apply substitutions
        log_fn(1, "Generating configuration files...")
        for template_file in glob.glob(os.path.join(template_dir, "*.template")):
            template_filename = os.path.basename(template_file)[:-len(".template")]
            log_fn(2, "Generating file \"%s\"..." % template_filename)
            with open(template_file, "r") as template_in, open(os.path.join(config_dir, template_filename), "w") as config_out:
                for line in template_in:
                    print(substitutions_pattern.sub(lambda m: substitutions[m.group(0)], line.rstrip()), file=config_out)
        log_fn(2, "Generating file \"master\"...")
        with open(os.path.join(config_dir, "master"), "w") as master_file:
            print(master, file=master_file)
        log_fn(2, "Generating file \"slaves\"...")
        with open(os.path.join(config_dir, "slaves"), "w") as slaves_file:
            for worker in workers:
                print(worker, file=slaves_file)
        log_fn(2, "Configuration files generated.")

        # Clean up previous Spark deployments
        log_fn(1, "Creating a clean environment on the master and workers...")
        local_spark_dir = "/local/%s/spark/" % substitutions["__USER__"]
        log_fn(2, "Purging \"%s\" on master (%s)..." % (local_spark_dir, master))
        util.execute_command_log(["ssh", master, 'rm -rf "%s"' % local_spark_dir])
        log_fn(2, "Purging \"%s\" on workers..." % local_spark_dir)
        for worker in workers:
            util.execute_command_log(['ssh', worker, 'rm -rf "%s"' % local_spark_dir])

        # Creating directory structure 
        log_fn(2, "Creating directory structure on master...")
        util.execute_command_log(['ssh', master, 'mkdir -p "%s"' % local_spark_dir])
        log_fn(2, "setting permissions on directory structure on master...")
        util.execute_command_log(['ssh', master, 'chmod 0770 "%s"' % local_spark_dir])
        log_fn(2, "Creating directory structure and setting permission on workers...")
        for worker in workers:
            util.execute_command_log(['ssh', worker, 'mkdir -p "%s"' % local_spark_dir])
            util.execute_command_log(['ssh', worker, 'chmod 0770 "%s"' % local_spark_dir])
        log_fn(2, "Clean environment set up.")

        # Start Spark
        log_fn(1, "Deploying Spark...")
        util.execute_command_log(['ssh', master, '%s/sbin/start-all.sh' % spark_home])

        log_fn(1, "Spark cluster deployed.")

        print(f"MASTER_NODE:{master}")

get_framework_registry().register_framework(SparkFramework())
get_framework_registry().framework("spark").add_version(SparkFrameworkVersion("2.4.0", "https://archive.apache.org/dist/spark/spark-2.4.0/spark-2.4.0-bin-hadoop2.6.tgz", "tgz", "spark-2.4.0-bin-hadoop2.6", "2.4.x"))
get_framework_registry().framework("spark").add_version(SparkFrameworkVersion("3.0.0", "https://archive.apache.org/dist/spark/spark-3.0.0/spark-3.0.0-bin-hadoop2.7.tgz", "tgz", "spark-3.0.0-bin-hadoop2.7", "2.4.x"))
get_framework_registry().framework("spark").add_version(SparkFrameworkVersion("3.0.2", "https://archive.apache.org/dist/spark/spark-3.0.2/spark-3.0.2-bin-hadoop2.7.tgz", "tgz", "spark-3.0.2-bin-hadoop2.7", "2.4.x"))
get_framework_registry().framework("spark").add_version(SparkFrameworkVersion("3.1.1", "https://apache.mirror.wearetriple.com/spark/spark-3.1.1/spark-3.1.1-bin-hadoop3.2.tgz", "tgz", "spark-3.1.1-bin-hadoop3.2", "2.4.x"))
get_framework_registry().framework("spark").add_version(SparkFrameworkVersion("custom", "https://github.com/kazemaksOG/spark-custom-scheduler.git", "git", "spark-custom", "custom"))
get_framework_registry().framework("spark").add_version(SparkFrameworkVersion("3.5.5-custom", "https://github.com/kazemaksOG/spark-3.5.5-custom", "git", "spark-3.5.5-custom", "custom"))
