import os, sys, argparse
from kubernetes import client, config
import requests
import time
from multiprocessing import Process


config.load_incluster_config()
v1 = client.CoreV1Api()
node_list = [] # global incase of future implementation of parallelism

# parser = argparse.ArgumentParser()
# parser.add_argument('--service', type=str, help='Autopilot healthchecks service name')
# parser.add_argument('--namespace', type=str, help='Autopilot healthchecks namespace')
# parser.add_argument('--node', type=str, help='Node that will run a healthcheck')

args = sys.argv
service = ''
namespace = ''
node = ''
for arg in args:
    if "service" in arg:
        service = arg.split('=')[1]
    elif 'namespace' in arg:
        namespace = arg.split('=')[1]
    elif 'node' in arg:
        node = arg.split('=')[1]


# get addresses in desired endpointslice (autopilot-healthchecks endpoints) based on which node(s) the user chooses
def get_addresses():
    endpoints = v1.list_namespaced_endpoints(namespace=namespace).items
    for endpointslice in endpoints:
        if endpointslice.metadata.name == service:
            print("EndpointSlice: " + str(endpointslice.metadata.name)) 

            # print('SUBSETS: ' + str(endpointslice.subsets)) # debug
            addresses = endpointslice.subsets[0].addresses
            if node == 'all':
                # print('ADDRESSES: ' + str(addresses)) # debug
                return addresses
            else:
                address_list = []
                for address in addresses:
                    if address.node_name == node:
                        address_list.append(address)
                        # print('ADDRESSES: ' + str(address_list)) # debug
                        return address_list
                print('Error: Issue with node choice. Choices include: \"all\", and the node name of a specific node.')
                raise SystemExit(2)


# runs healthchecks at each endpoint (there is one endpoint in each node)
def run_tests(addresses):
    for address in addresses:
        print("\nEndpoint: " + str(address.ip)) # debug
        daemon_node = str(address.node_name)
        print("\nNode: ", daemon_node) # debug
        node_list.append(daemon_node)
        
        # create url for pciebw, network, and remapped tests
        # ex: curl http://10.128.11.100:3333/status?host=dev-ppv5g-worker-3-with-secondary-thlkf
        status_test = 'http://' + str(address.ip) + ':3333/status?host=' + str(daemon_node)
        
        # run status test
        print('\nStatus test: ' + status_test)
        print('\nStatus test response: ', get_requests(status_test))
        print("\n-------------------------------------\n") # separator
            
    print('Node list: ')
    for node in node_list: 
        print('\n', node)


# rest api calls for healthcheck
def get_requests(url):
    page = ''
    while page == '':
        try:
            page = requests.get(url)
            break
        except:
            print('Connection refused by server..')
            print('sleeping for 5 seconds')
            time.sleep(5)
            continue
    return page.text


if __name__ == "__main__":
    run_tests(get_addresses())
