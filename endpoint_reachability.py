# Requires Python 3.6 or later as this utilizes f string formatting
import platform
import subprocess
import pandas as pd
from pprint import pprint
import threading
from queue import Queue
import argparse

class Endpoint_Reachability():

    def __init__(self):
        '''
        Straightforward, just call to do_work
        '''
        args = argparse.ArgumentParser()
        args.add_argument('--host_file',
                          help='name of the host file to read in, default is endpoint reachability testing.xlsx',
                          default='endpoint reachability testing.xlsx')
        arguments = args.parse_args()
        args_dictionary = vars(arguments)

        thread_count_max = 20

        # reachable hosts list
        self.reachable_hosts = []
        # unreachable hosts list
        self.unreachable_hosts = []

        # set up a work queue to use
        self.work_queue = Queue(maxsize=0)

        host_file = args_dictionary['host_file']
        # read excel into dataframe
        hosts = pd.read_excel(host_file)

        # see if we're using Windows or Linux
        os_type = platform.system().lower()

        for index, host in hosts.iterrows():
            host_data = {
                'endpoint_ip': host['endpoint_ip'],
                'test_method': host['test_method'],
                'command': self.get_command(ip=host['endpoint_ip'], os_type=os_type, test_method=host['test_method'])
            }
            # append host data to the queue
            self.work_queue.put(host_data)

        # start some threads
        for i in range(thread_count_max):
            connectivity_thread = threading.Thread(
                target=self.do_work,
                name=f'thread_number_{i}'
            )
            # set daemon
            connectivity_thread.setDaemon(True)
            # start the thread
            connectivity_thread.start()

        # wait for all to return
        self.work_queue.join()

        # print off the results
        self.return_results(unreachable_hosts=self.unreachable_hosts, reachable_hosts=self.reachable_hosts)

    def do_work(self):
        '''
        performs the reachability check
        :return:
        '''

        while not self.work_queue.empty():
            # get info from queue
            host_data = self.work_queue.get()
            # set some variables
            ip = host_data['endpoint_ip']
            test_method = host_data['test_method']
            command = host_data['command']

            print('Testing for host {ip} using method {method}'.format(
                ip=ip,
                method=test_method
            ))
            if host_data['test_method'] == 'ping':
                try:
                    subprocess.check_output(command)
                    #print(f'host {ip} is REACHABLE')
                    self.reachable_hosts.append(ip)
                except subprocess.CalledProcessError:
                    #print(f'host {ip} is UNREACHABLE!')
                    self.unreachable_hosts.append(ip)
                finally:
                    self.work_queue.task_done()
            elif test_method == 'traceroute':
                try:
                    subprocess.check_output(command)
                    subprocess.call(command)
                except subprocess.CalledProcessError:
                    print(f'Traceroute to host {ip} failed...he\'s Dead Jim')
                finally:
                    self.work_queue.task_done()

    def get_command(self, os_type, test_method, ip):
        '''
        take os_type, test_method, and ip and return command for subprocess to use
        :param os_type:
        :param test_method:
        :param ip:
        :return:
        '''
        # ping
        if os_type == 'windows' and test_method == 'ping':
            command = ['ping', '-n', '2', ip]
        elif os_type == 'linux' and test_method == 'ping':
            command = ['ping', '-c', '2', ip]
        # traceroute
        elif os_type == 'windows' and test_method == 'traceroute':
            command = ['tracert', '-d', '-h', '10', ip]
        # this is iffy, if the linux distro doesn't have traceroute installed by default we'll fail here
        elif os_type == 'linux' and test_method == 'traceroute':
            command = ['traceroute', '-n', '-m', '10', ip]
        return command

    def return_results(self, unreachable_hosts, reachable_hosts):
        '''
        Return the results from the reachability testing
        :param unreachable_hosts:
        :param reachable_hosts:
        :return:
        '''
        # total number of hosts
        total = len(unreachable_hosts) + len(reachable_hosts)
        percentage_unreachable = len(unreachable_hosts) / total
        # print out reachable hosts
        print('*' * 100 + '\nThe list of reachable hosts is below:')
        pprint(reachable_hosts, indent=1)
        # print out unreachable hosts
        print('*' * 100 + '\nThe list of UNREACHABLE hosts is below:')
        pprint(unreachable_hosts, indent=1)
        # Just drop the decimal not too worried about it here with the percentage
        print(f'total of unreachable hosts is {int(percentage_unreachable * 100)}%')

# kick this off
if __name__ == '__main__':
    tester = Endpoint_Reachability()