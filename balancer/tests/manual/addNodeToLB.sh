URL=http://localhost:8181/foo/loadbalancers
curl -X PUT -H "Content-Type: application/json" -d@addNodeCommand $URL/$1/nodes
